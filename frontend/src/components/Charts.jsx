import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine,
  LineChart, Line, PieChart, Pie, Cell, Legend,
} from "recharts";
import ChartCard from "./ChartCard";
import { gradeDistribution, PASS_MARK } from "../utils/grades";
import { courseAverages, gpaBySemester } from "../utils/students";

// Colours come from CSS variables so they follow the light/dark theme.
const GRADE_COLORS = {
  A: "var(--grade-a)",
  B: "var(--grade-b)",
  C: "var(--grade-c)",
  D: "var(--grade-d)",
  F: "var(--grade-f)",
};

function Charts({ students }) {
  const gpaData = gpaBySemester(students);
  const gradeData = gradeDistribution(students).filter((g) => g.students > 0);
  const courseData = courseAverages(students);

  return (
    <div className="charts">
      <ChartCard title="Average GPA by semester" empty={gpaData.length === 0}>
        <LineChart data={gpaData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="semester" />
          <YAxis domain={[0, 4]} />
          <Tooltip />
          <Line type="monotone" dataKey="gpa" name="Average GPA" stroke="var(--chart-line)" strokeWidth={2} dot />
        </LineChart>
      </ChartCard>

      <ChartCard title="Grade distribution" empty={gradeData.length === 0}>
        <PieChart>
          <Pie data={gradeData} dataKey="students" nameKey="grade" outerRadius="75%" label={({ grade, students: n }) => `${grade}: ${n}`}>
            {gradeData.map((entry) => (
              <Cell key={entry.grade} fill={GRADE_COLORS[entry.grade]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ChartCard>

      <ChartCard title="Average score by course" empty={courseData.length === 0}>
        <BarChart data={courseData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="course" interval={0} tick={{ fontSize: 12 }} />
          <YAxis domain={[0, 100]} />
          <Tooltip />
          <ReferenceLine y={PASS_MARK} stroke="var(--alert)" strokeDasharray="4 4" label={{ value: "Pass mark", position: "insideTopRight", fontSize: 12 }} />
          <Bar dataKey="avgScore" name="Average score" fill="var(--chart-bar)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ChartCard>
    </div>
  );
}

export default Charts;
