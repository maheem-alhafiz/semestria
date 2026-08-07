import type { AssessmentRead, GradeScaleCutoffItem, LetterGrade } from "@/types/api";

// Fixed, standardized University of Manitoba grade-point scale (Registrar's
// Office "Grades" page) -- NOT student-editable, unlike the percent cutoffs
// in GradeScaleCutoffItem (UM doesn't publish a universal percent table,
// see backend app.models.assessment's docstring).
export const GRADE_POINTS: Record<LetterGrade, number> = {
  "A+": 4.5,
  A: 4.0,
  "B+": 3.5,
  B: 3.0,
  "C+": 2.5,
  C: 2.0,
  D: 1.0,
  Fail: 0.0,
};

export interface CourseGradeProjection {
  // % of the course's total graded weight that's actually been graded so far.
  gradedWeightPercent: number;
  // Weighted average of graded work only, 0-100. Null if nothing graded yet.
  currentAveragePercent: number | null;
  // currentAveragePercent projected across the rest of the course, assuming
  // the same rate continues. Same value as currentAveragePercent today --
  // kept separate so a smarter projection can replace just this later
  // without touching callers.
  predictedFinalPercent: number | null;
  predictedLetter: LetterGrade | null;
  predictedGpaPoints: number | null;
}

export function projectCourseGrade(
  assessments: AssessmentRead[],
  gradeScale: GradeScaleCutoffItem[]
): CourseGradeProjection {
  const graded = assessments.filter((a) => a.grade_received != null && a.weight_percent != null);
  const gradedWeightPercent = graded.reduce((sum, a) => sum + (a.weight_percent ?? 0), 0);

  if (gradedWeightPercent <= 0) {
    return {
      gradedWeightPercent: 0,
      currentAveragePercent: null,
      predictedFinalPercent: null,
      predictedLetter: null,
      predictedGpaPoints: null,
    };
  }

  const weightedPoints = graded.reduce(
    (sum, a) => sum + ((a.weight_percent ?? 0) * (a.grade_received ?? 0)) / 100,
    0
  );
  const currentAveragePercent = (weightedPoints / gradedWeightPercent) * 100;
  const predictedFinalPercent = currentAveragePercent;
  const letter = percentToLetter(predictedFinalPercent, gradeScale);

  return {
    gradedWeightPercent,
    currentAveragePercent,
    predictedFinalPercent,
    predictedLetter: letter,
    predictedGpaPoints: letter ? GRADE_POINTS[letter] : null,
  };
}

export function percentToLetter(
  percent: number,
  gradeScale: GradeScaleCutoffItem[]
): LetterGrade | null {
  if (gradeScale.length === 0) return null;
  const sorted = [...gradeScale].sort((a, b) => b.min_percent - a.min_percent);
  const match = sorted.find((c) => percent >= c.min_percent);
  return (match ?? sorted[sorted.length - 1])?.letter_grade ?? null;
}

// Credit-hour-weighted average across courses that have a prediction yet.
// Courses with nothing graded are excluded (nothing to weight in), same
// as how UM's own TGPA only counts completed courses.
export function projectTermGpa(
  courses: { creditHours: number; projection: CourseGradeProjection }[]
): number | null {
  const withGrades = courses.filter((c) => c.projection.predictedGpaPoints != null);
  if (withGrades.length === 0) return null;

  const totalCredits = withGrades.reduce((sum, c) => sum + c.creditHours, 0);
  if (totalCredits <= 0) return null;

  const totalPoints = withGrades.reduce(
    (sum, c) => sum + (c.projection.predictedGpaPoints ?? 0) * c.creditHours,
    0
  );
  return totalPoints / totalCredits;
}
