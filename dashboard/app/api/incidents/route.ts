import { NextResponse } from "next/server";
import { Pool } from "pg";

export async function GET() {
  try {
    const pool = new Pool({
      connectionString: process.env.DATABASE_URL || "postgresql://postgres:password@db:5432/agenticmesh"
    });

    const result = await pool.query(`
      SELECT 
        i.incident_id,
        i.status,
        i.created_at,
        r.root_cause,
        r.confidence_score,
        r.faulty_file,
        r.code_snippet,
        r.suggested_fix_diff
      FROM incidents i
      LEFT JOIN rca_results r ON i.id = r.incident_id
      ORDER BY i.created_at DESC
      LIMIT 50
    `);
    
    const mapped = result.rows.map(row => ({
      incident_id: row.incident_id,
      status: row.status,
      root_cause: row.root_cause || "Pending RCA",
      confidence_score: row.confidence_score || 0,
      faulty_code_block: { file: row.faulty_file, code_snippet: row.code_snippet },
      suggested_fix: { diff: row.suggested_fix_diff }
    }));

    await pool.end();
    return NextResponse.json(mapped);
  } catch (error) {
    console.error("Failed to fetch incidents", error);
    return NextResponse.json({ error: "Failed to fetch incidents" }, { status: 500 });
  }
}
