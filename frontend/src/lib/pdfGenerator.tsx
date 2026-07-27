import React from "react";
import { Document, Page, Text, View, StyleSheet, pdf } from "@react-pdf/renderer";
import { getPlan, getCourseSections, getTerms } from "./api";
import type { PlanSummary, CourseSections, PlanItemRead, Term } from "@/types/api";

// --- CONSTANTS & TYPES ---
const START_HOUR = 8;  // 8 AM
const END_HOUR = 18;   // 6 PM
const HOUR_HEIGHT = 40; // pixels per hour in the grid
const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"] as const;

interface EventData {
  id: string;
  title: string;
  days: string[];
  startHour: number;
  endHour: number;
  timeString: string;
}

// --- PDF STYLES ---
const styles = StyleSheet.create({
  page: { padding: 30, fontFamily: "Helvetica", backgroundColor: "#FFFFFF" },
  header: { marginBottom: 20, borderBottom: "1px solid #e5e5e5", paddingBottom: 10, flexDirection: "row", justifyContent: "space-between", alignItems: "flex-end" },
  brand: { fontSize: 24, fontWeight: "bold", color: "#171717", letterSpacing: -1 },
  brandAccent: { color: "#0d9488" },
  termTitle: { fontSize: 14, color: "#525252", fontWeight: "bold" },
  
  // Grid Styles
  gridContainer: { flexDirection: "row", height: (END_HOUR - START_HOUR) * HOUR_HEIGHT + 20, border: "1px solid #e5e5e5", borderRadius: 4, marginBottom: 20 },
  timeColumn: { width: 40, borderRight: "1px solid #e5e5e5", backgroundColor: "#fafafa" },
  timeLabel: { height: HOUR_HEIGHT, fontSize: 8, color: "#a3a3a3", textAlign: "right", paddingRight: 4, paddingTop: 4 },
  dayColumn: { flex: 1, borderRight: "1px solid #e5e5e5", position: "relative" },
  dayHeader: { height: 20, borderBottom: "1px solid #e5e5e5", textAlign: "center", fontSize: 9, padding: 4, backgroundColor: "#fafafa", color: "#525252", fontWeight: "bold" },
  
  // Event Block Styles
  eventBlock: { position: "absolute", left: 1, right: 1, backgroundColor: "#0d9488", borderRadius: 2, padding: 3, overflow: "hidden" },
  eventTitle: { fontSize: 7, color: "#ffffff", fontWeight: "bold", marginBottom: 2 },
  eventTime: { fontSize: 6, color: "#ffffff", opacity: 0.9 },

  // Table Styles
  sectionTitle: { fontSize: 12, fontWeight: "bold", color: "#171717", marginBottom: 6 },
  table: { width: "100%", border: "1px solid #e5e5e5", borderRadius: 4 },
  tableHeader: { flexDirection: "row", backgroundColor: "#fafafa", borderBottom: "1px solid #e5e5e5", padding: 6 },
  tableRow: { flexDirection: "row", borderBottom: "1px solid #e5e5e5", padding: 6 },
  colCRN: { width: "15%", fontSize: 9, color: "#525252" },
  colCourse: { width: "40%", fontSize: 9, color: "#171717", fontWeight: "bold" },
  colCredits: { width: "15%", fontSize: 9, color: "#525252", textAlign: "center" },
  colInstructor: { width: "30%", fontSize: 9, color: "#525252" },
});

// --- HELPER FUNCTIONS ---
function timeToDecimal(timeStr: string): number {
  const parts = timeStr.split(":");
  const hours = Number(parts[0] || 0);
  const minutes = Number(parts[1] || 0);
  return hours + (minutes / 60);
}

function formatTime(timeStr: string): string {
  const parts = timeStr.split(":");
  const h = Number(parts[0] || 0);
  const minutes = parts[1] || "00";
  const ampm = h >= 12 ? "PM" : "AM";
  const formattedH = h % 12 === 0 ? 12 : h % 12;
  return `${formattedH}:${minutes} ${ampm}`;
}

// --- PDF COMPONENT ---
interface PlanDocumentProps {
  planName: string;
  termsData: { 
    termLabel: string; 
    items: { item: PlanItemRead; details: CourseSections }[];
    events: EventData[];
  }[];
}

const PlanDocument = ({ planName, termsData }: PlanDocumentProps) => (
  <Document>
    {termsData.map((termData, index) => (
      <Page key={index} size="LETTER" style={styles.page}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.brand}>semestria<Text style={styles.brandAccent}>.</Text></Text>
          <Text style={styles.termTitle}>{planName} — {termData.termLabel}</Text>
        </View>

        {/* Visual Grid */}
        <View style={styles.gridContainer}>
          {/* Time Labels */}
          <View style={styles.timeColumn}>
            <View style={styles.dayHeader}><Text></Text></View>
            {Array.from({ length: END_HOUR - START_HOUR }).map((_, i) => (
              <Text key={i} style={styles.timeLabel}>
                {START_HOUR + i > 12 ? START_HOUR + i - 12 : START_HOUR + i} {START_HOUR + i >= 12 ? 'PM' : 'AM'}
              </Text>
            ))}
          </View>

          {/* Day Columns */}
          {DAYS.map((day) => (
            <View style={styles.dayColumn} key={day}>
              <View style={styles.dayHeader}>
                <Text>{day.charAt(0).toUpperCase() + day.slice(1, 3)}</Text>
              </View>
              {termData.events
                .filter((e) => e.days.includes(day))
                .map((e, idx) => {
                  const top = (e.startHour - START_HOUR) * HOUR_HEIGHT + 20; // +20 for dayHeader height
                  const height = (e.endHour - e.startHour) * HOUR_HEIGHT;
                  
                  // Skip rendering if outside grid bounds
                  if (e.startHour < START_HOUR || e.endHour > END_HOUR) return null;

                  return (
                    <View key={`${e.id}-${idx}`} style={[styles.eventBlock, { top, height }]}>
                      <Text style={styles.eventTitle}>{e.title}</Text>
                      <Text style={styles.eventTime}>{e.timeString}</Text>
                    </View>
                  );
                })}
            </View>
          ))}
        </View>

        {/* Course Summary Table for THIS Term */}
        <View>
          <Text style={styles.sectionTitle}>Course Summary</Text>
          <View style={styles.table}>
            <View style={styles.tableHeader}>
              <Text style={styles.colCRN}>CRN</Text>
              <Text style={styles.colCourse}>Course</Text>
              <Text style={styles.colCredits}>Credits</Text>
              <Text style={styles.colInstructor}>Instructor</Text>
            </View>
            
            {termData.items.map(({ item, details }) => {
              const chosenCrns = new Set(item.chosen_sections.map((s) => s.crn));
              const selectedOptions = details.groups
                .flatMap((g) => g.slots)
                .flatMap((s) => s.options)
                .filter((o) => chosenCrns.has(o.crn));

              return selectedOptions.map((opt) => (
                <View style={styles.tableRow} key={opt.crn}>
                  <Text style={styles.colCRN}>{opt.crn}</Text>
                  <Text style={styles.colCourse}>{details.subject} {details.course_number}</Text>
                  <Text style={styles.colCredits}>{details.credit_hours}</Text>
                  <Text style={styles.colInstructor}>{opt.instructor || "TBA"}</Text>
                </View>
              ));
            })}
          </View>
        </View>
      </Page>
    ))}
  </Document>
);

// --- GENERATOR FUNCTION ---
export async function downloadPlanPDF(planSummary: PlanSummary) {
  try {
    const [plan, termList] = await Promise.all([
      getPlan(planSummary.id),
      getTerms()
    ]);
    
    const termMap = Object.fromEntries(termList.map((t) => [t.term_code, t.description]));

    // Group items by term_code
    const itemsByTerm = plan.items.reduce<Record<string, PlanItemRead[]>>((acc, item) => {
      const termArr = acc[item.term_code] ?? [];
      termArr.push(item);
      acc[item.term_code] = termArr;
      return acc;
    }, {});

    // Build hydrated data per term
    const termsData = await Promise.all(
      Object.entries(itemsByTerm).map(async ([termCode, items]) => {
        const hydratedItems = await Promise.all(
          items.map(async (item) => {
            const details = await getCourseSections(item.course_id, item.term_code);
            return { item, details };
          })
        );

        // Build grid events
        const events: EventData[] = [];
        for (const { item, details } of hydratedItems) {
          const chosenCrns = new Set(item.chosen_sections.map((s) => s.crn));
          for (const group of details.groups) {
            for (const slot of group.slots) {
              for (const option of slot.options) {
                if (!chosenCrns.has(option.crn)) continue;
                for (const mt of option.meeting_times) {
                  if (!mt.start_time || !mt.end_time) continue;
                  
                  const activeDays = DAYS.filter((d) => mt[d]);
                  if (activeDays.length > 0) {
                    events.push({
                      id: `${option.crn}-${mt.meeting_type}`,
                      title: `${details.subject} ${details.course_number}`,
                      days: activeDays,
                      startHour: timeToDecimal(mt.start_time),
                      endHour: timeToDecimal(mt.end_time),
                      timeString: `${formatTime(mt.start_time)} - ${formatTime(mt.end_time)}`
                    });
                  }
                }
              }
            }
          }
        }

        return {
          termLabel: termMap[termCode] || termCode,
          items: hydratedItems,
          events,
        };
      })
    );

    const blob = await pdf(<PlanDocument planName={plan.name} termsData={termsData} />).toBlob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${plan.name.replace(/\s+/g, "_")}_Schedule.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error("Failed to generate PDF:", err);
    alert("Could not generate PDF document.");
  }
}