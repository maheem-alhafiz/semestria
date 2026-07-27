import React from "react";
import { Document, Page, Text, View, StyleSheet, pdf } from "@react-pdf/renderer";
import { getPlan, getCourseSections } from "./api";
import type { PlanSummary, CourseSections, PlanItemRead } from "@/types/api";

// --- PDF STYLES ---
const styles = StyleSheet.create({
  page: { padding: 40, fontFamily: "Helvetica", backgroundColor: "#FFFFFF" },
  header: { marginBottom: 30, borderBottom: "2px solid #0d9488", paddingBottom: 10 },
  brand: { fontSize: 24, fontWeight: "bold", color: "#171717" },
  brandAccent: { color: "#0d9488" },
  planName: { fontSize: 14, color: "#525252", marginTop: 4 },
  sectionTitle: { fontSize: 16, fontWeight: "bold", color: "#171717", marginBottom: 10, marginTop: 20 },
  
  // Table Styles
  table: { width: "100%", border: "1px solid #e5e5e5", borderRadius: 4, marginTop: 10 },
  tableHeader: { flexDirection: "row", backgroundColor: "#f5f5f5", borderBottom: "1px solid #e5e5e5", padding: 8 },
  tableRow: { flexDirection: "row", borderBottom: "1px solid #e5e5e5", padding: 8 },
  colCRN: { width: "15%", fontSize: 10, color: "#525252" },
  colCourse: { width: "50%", fontSize: 10, color: "#171717", fontWeight: "bold" },
  colCredits: { width: "15%", fontSize: 10, color: "#525252", textAlign: "center" },
  colInstructor: { width: "20%", fontSize: 10, color: "#525252" },
});

// --- PDF COMPONENT ---
interface PlanDocumentProps {
  planName: string;
  hydratedItems: { item: PlanItemRead; details: CourseSections }[];
}

const PlanDocument = ({ planName, hydratedItems }: PlanDocumentProps) => (
  <Document>
    <Page size="LETTER" style={styles.page}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.brand}>Semestria<Text style={styles.brandAccent}>.</Text></Text>
        <Text style={styles.planName}>{planName}</Text>
      </View>

      {/* Course Summary Table */}
      <View>
        <Text style={styles.sectionTitle}>Course Summary</Text>
        <View style={styles.table}>
          {/* Table Header */}
          <View style={styles.tableHeader}>
            <Text style={styles.colCRN}>CRN</Text>
            <Text style={styles.colCourse}>Course</Text>
            <Text style={styles.colCredits}>Credits</Text>
            <Text style={styles.colInstructor}>Instructor</Text>
          </View>
          
          {/* Table Rows */}
          {hydratedItems.map(({ item, details }) => {
            // Find chosen options to display
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
  </Document>
);

// --- GENERATOR FUNCTION ---
export async function downloadPlanPDF(planSummary: PlanSummary) {
  try {
    const plan = await getPlan(planSummary.id);
    
    const hydratedItems = await Promise.all(
      plan.items.map(async (item) => {
        const details = await getCourseSections(item.course_id, item.term_code);
        return { item, details };
      })
    );

    const blob = await pdf(<PlanDocument planName={plan.name} hydratedItems={hydratedItems} />).toBlob();
    
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${plan.name.replace(/\s+/g, "_")}_Overview.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error("Failed to generate PDF:", err);
    alert("Could not generate PDF document.");
  }
}