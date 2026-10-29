import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

/**
 * Downloads the autonomous report as a clean, professionally formatted Markdown file.
 */
export function exportReportToMarkdown(report, datasetInfo) {
  if (!report) return;

  const datasetName = datasetInfo?.tables?.[0] || report.table_name || 'dataset';
  const timestamp = report.generated_at || new Date().toISOString().replace('T', ' ').slice(0, 19);

  let md = `# Executive Intelligence Dossier: ${datasetName.toUpperCase()}\n`;
  md += `*Generated automatically by Autonomous Data Analyst Agent*\n`;
  md += `*Timestamp: ${timestamp}*\n\n`;

  md += `## 1. Executive Summary\n`;
  md += `${report.executive_summary || 'No summary available.'}\n\n`;

  if (report.kpi_metrics && report.kpi_metrics.length > 0) {
    md += `## 2. Core Business Metrics & KPI Anchors\n`;
    md += `| Metric Label | Value | Context |\n`;
    md += `| :--- | :--- | :--- |\n`;
    report.kpi_metrics.forEach((k) => {
      md += `| **${k.label}** | \`${k.value}\` | ${k.subtext || '-'} |\n`;
    });
    md += `\n`;
  }

  if (report.top_findings && report.top_findings.length > 0) {
    md += `## 3. Discovered Strategic Findings\n`;
    report.top_findings.forEach((finding, idx) => {
      md += `${idx + 1}. **Finding**: ${finding}\n`;
    });
    md += `\n`;
  }

  if (report.anomalies_detected && report.anomalies_detected.length > 0) {
    md += `## 4. Anomalies & Outlier Diagnostic Scan\n`;
    md += `| Dimension / Metric | Severity | Diagnostic Details |\n`;
    md += `| :--- | :--- | :--- |\n`;
    report.anomalies_detected.forEach((a) => {
      md += `| **${a.column}** | \`${a.severity}\` | ${a.details} |\n`;
    });
    md += `\n`;
  } else {
    md += `## 4. Anomalies & Outlier Diagnostic Scan\n`;
    md += `*No extreme statistical anomalies detected within IQR 1.5x boundaries.*\n\n`;
  }

  if (report.correlations && report.correlations.length > 0) {
    md += `## 5. Statistical Correlations & Linkages\n`;
    md += `| Variable 1 | Variable 2 | Pearson r | Strength & Direction |\n`;
    md += `| :--- | :--- | :--- | :--- |\n`;
    report.correlations.forEach((c) => {
      const sign = c.pearson > 0 ? `+${c.pearson}` : `${c.pearson}`;
      md += `| ${c.var1} | ${c.var2} | \`${sign}\` | ${c.strength} ${c.direction} |\n`;
    });
    md += `\n`;
  }

  if (report.recommended_actions && report.recommended_actions.length > 0) {
    md += `## 6. Recommended Next-Step Inquiries\n`;
    report.recommended_actions.forEach((act, idx) => {
      md += `- [ ] ${act}\n`;
    });
    md += `\n`;
  }

  md += `---\n`;
  md += `*Autonomous Data Analyst Agent • Multi-Agent Analytics Engine powered by DuckDB & LangGraph*\n`;

  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Executive_Briefing_${datasetName}_${new Date().toISOString().slice(0, 10)}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Exports the rendered report element to a high-resolution, multi-page branded PDF.
 */
export async function exportReportToPDF(elementRef, report, datasetInfo) {
  if (!elementRef || !report) return;

  const datasetName = datasetInfo?.tables?.[0] || report.table_name || 'dataset';

  // Create canvas using html2canvas with scale: 2 for retina / high-resolution crispness
  const canvas = await html2canvas(elementRef, {
    scale: 2,
    useCORS: true,
    logging: false,
    backgroundColor: '#0f172a', // Clean dark theme background
    windowWidth: elementRef.scrollWidth,
  });

  const imgData = canvas.toDataURL('image/png');
  const pdf = new jsPDF('p', 'mm', 'a4');
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();

  const margin = 10;
  const contentWidth = pageWidth - margin * 2;
  const contentHeight = (canvas.height * contentWidth) / canvas.width;

  let heightLeft = contentHeight;
  let position = margin;
  let page = 1;

  // Header banner on first page
  pdf.addImage(imgData, 'PNG', margin, position, contentWidth, contentHeight, '', 'FAST');
  heightLeft -= pageHeight;

  while (heightLeft > 0) {
    position = heightLeft - contentHeight + margin;
    pdf.addPage();
    page++;
    pdf.addImage(imgData, 'PNG', margin, position, contentWidth, contentHeight, '', 'FAST');
    heightLeft -= pageHeight;
  }

  const filename = `Autonomous_Executive_Briefing_${datasetName}_${new Date().toISOString().slice(0, 10)}.pdf`;
  pdf.save(filename);
}

/**
 * Copies the executive summary and key findings to the user's clipboard.
 */
export async function copyReportSummaryToClipboard(report) {
  if (!report) return false;

  let text = `⚡ AUTONOMOUS DATA ANALYST - EXECUTIVE SUMMARY\n\n`;
  text += `${report.executive_summary}\n\n`;

  if (report.kpi_metrics?.length) {
    text += `KEY METRICS:\n`;
    report.kpi_metrics.forEach((k) => {
      text += `• ${k.label}: ${k.value} (${k.subtext || ''})\n`;
    });
    text += `\n`;
  }

  if (report.top_findings?.length) {
    text += `CORE FINDINGS:\n`;
    report.top_findings.forEach((f, i) => {
      text += `${i + 1}. ${f}\n`;
    });
  }

  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    console.error('Clipboard copy failed:', err);
    return false;
  }
}
