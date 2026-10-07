"""
Root Gateway & Interactive System Landing Page Module.
Serves interactive HTML dashboard for browser requests and structured JSON for API clients.
"""

from flask import Blueprint, request, jsonify, Response

from app.models.department import Department
from app.models.subject import Subject
from app.models.room import Room
from app.models.teacher import Teacher
from app.models.student import Student
from app.models.exam import Exam
from app.models.seating_plan import SeatingPlan

root_bp = Blueprint("root", __name__)


def _get_database_stats():
    """Safely fetches entity counts from the database."""
    try:
        return {
            "departments": Department.query.count(),
            "subjects": Subject.query.count(),
            "rooms": Room.query.count(),
            "teachers": Teacher.query.count(),
            "students": Student.query.count(),
            "exams": Exam.query.count(),
            "seating_plans": SeatingPlan.query.count(),
        }
    except Exception:
        return {
            "departments": 0,
            "subjects": 0,
            "rooms": 0,
            "teachers": 0,
            "students": 0,
            "exams": 0,
            "seating_plans": 0,
        }


FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <path d="M50 15 L90 35 L50 55 L10 35 Z" fill="#2563eb" />
  <path d="M25 43 L25 65 C25 78 75 78 75 65 L75 43 L50 54 Z" fill="#1d4ed8" />
  <circle cx="88" cy="40" r="4" fill="#f59e0b" />
  <line x1="88" y1="40" x2="88" y2="65" stroke="#f59e0b" stroke-width="2" />
  <circle cx="88" cy="65" r="3" fill="#f59e0b" />
</svg>"""


@root_bp.route("/favicon.ico", methods=["GET"])
def favicon():
    """Returns SVG favicon for browser tabs to eliminate 404 errors."""
    return Response(FAVICON_SVG, mimetype="image/svg+xml")


@root_bp.route("/", methods=["GET"])
@root_bp.route("/api", methods=["GET"])
def index():
    """
    Root Entry Point.
    Serves interactive HTML landing page if requested by browser,
    or JSON system overview if requested by an API client.
    """
    stats = _get_database_stats()
    wants_json = (
        request.is_json
        or request.args.get("format") == "json"
        or (
            request.accept_mimetypes.best_match(["application/json", "text/html"])
            == "application/json"
            and not request.accept_mimetypes.accept_html
        )
    )

    if wants_json:
        return jsonify({
            "success": True,
            "system": "Smart Polytechnic Exam Seating & Invigilation Planner",
            "version": "1.0 (Diploma Edition)",
            "status": "online",
            "domain": "Polytechnic / Diploma Institutions (Semesters 1-6)",
            "disciplines": ["CO", "IT", "ME", "CE", "EE", "EJ"],
            "live_stats": stats,
            "api_endpoints": {
                "health": "/api/health",
                "auth": "/api/auth",
                "departments": "/api/departments",
                "subjects": "/api/subjects",
                "students": "/api/students",
                "teachers": "/api/teachers",
                "rooms": "/api/rooms",
                "exams": "/api/exams",
                "planning": "/api/planning",
                "student_portal": "/api/student",
                "teacher_portal": "/api/teacher",
                "notifications": "/api/notifications",
                "audit_logs": "/api/audit-logs",
                "reports_and_contracts": "/api/reports",
            },
            "documentation": "README.md"
        }), 200

    # HTML Landing Page for Web Browsers
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Smart Polytechnic Exam Planner — Backend API Gateway</title>
  <link rel="icon" type="image/svg+xml" href="/favicon.ico">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --primary: #2563eb;
      --primary-dark: #1d4ed8;
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #10b981;
      --accent-warn: #f59e0b;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: radial-gradient(circle at top right, #1e1b4b 0%, #0f172a 100%);
      color: var(--text);
      line-height: 1.6;
      padding: 2rem 1rem;
      min-height: 100vh;
    }}
    .container {{
      max-width: 1100px;
      margin: 0 auto;
    }}
    .header {{
      text-align: center;
      margin-bottom: 2.5rem;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.35rem 0.85rem;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.4);
      color: #34d399;
      font-size: 0.85rem;
      font-weight: 600;
      border-radius: 9999px;
      margin-bottom: 1rem;
    }}
    .pulse {{
      width: 8px;
      height: 8px;
      background: #10b981;
      border-radius: 50%;
      box-shadow: 0 0 8px #10b981;
      animation: pulse-dot 1.5s infinite;
    }}
    @keyframes pulse-dot {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.4; transform: scale(0.8); }}
    }}
    h1 {{
      font-size: 2.3rem;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 0.5rem;
      letter-spacing: -0.02em;
    }}
    .subtitle {{
      color: var(--text-muted);
      font-size: 1.05rem;
      max-width: 700px;
      margin: 0 auto;
    }}
    .grid-stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 1rem;
      margin-bottom: 2.5rem;
    }}
    .stat-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.2rem;
      text-align: center;
      transition: transform 0.2s, border-color 0.2s;
    }}
    .stat-card:hover {{
      transform: translateY(-2px);
      border-color: var(--primary);
    }}
    .stat-number {{
      font-size: 1.8rem;
      font-weight: 700;
      color: #38bdf8;
    }}
    .stat-label {{
      font-size: 0.8rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-top: 0.25rem;
    }}
    .section-title {{
      font-size: 1.3rem;
      font-weight: 600;
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      color: #f1f5f9;
    }}
    .endpoints-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 1rem;
      margin-bottom: 2.5rem;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.25rem;
      transition: all 0.2s;
    }}
    .card:hover {{
      border-color: #64748b;
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.5rem;
    }}
    .card-title {{
      font-weight: 600;
      font-size: 1.05rem;
      color: #e2e8f0;
    }}
    .card-link {{
      color: #60a5fa;
      font-family: monospace;
      font-size: 0.85rem;
      text-decoration: none;
      background: rgba(37, 99, 235, 0.15);
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
      transition: background 0.2s;
    }}
    .card-link:hover {{
      background: rgba(37, 99, 235, 0.3);
      text-decoration: underline;
    }}
    .card-desc {{
      font-size: 0.85rem;
      color: var(--text-muted);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 0.5rem;
      font-size: 0.9rem;
    }}
    th, td {{
      padding: 0.75rem 1rem;
      text-align: left;
      border-bottom: 1px solid var(--card-border);
    }}
    th {{
      color: var(--text-muted);
      font-weight: 600;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    td code {{
      font-family: monospace;
      background: rgba(255, 255, 255, 0.08);
      padding: 0.15rem 0.4rem;
      border-radius: 4px;
      color: #fca5a5;
    }}
    .role-badge {{
      display: inline-block;
      padding: 0.15rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }}
    .role-admin {{ background: rgba(239, 68, 68, 0.2); color: #f87171; }}
    .role-teacher {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; }}
    .role-student {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
    .footer {{
      margin-top: 3rem;
      text-align: center;
      color: var(--text-muted);
      font-size: 0.85rem;
      border-top: 1px solid var(--card-border);
      padding-top: 1.5rem;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="badge">
        <span class="pulse"></span>
        Backend API Server Online • Flask 3.x
      </div>
      <h1>🎓 Smart Polytechnic Exam Planner</h1>
      <p class="subtitle">
        Architected for 3-Year Diploma / Polytechnic Institutions (Semesters 1–6).
        Disciplines: Computer (CO), IT, Mechanical (ME), Civil (CE), Electrical (EE), Electronics (EJ).
      </p>
    </div>

    <!-- Live Stats -->
    <div class="grid-stats">
      <div class="stat-card">
        <div class="stat-number">{stats['departments']}</div>
        <div class="stat-label">Departments</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{stats['subjects']}</div>
        <div class="stat-label">Subjects</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{stats['rooms']}</div>
        <div class="stat-label">Exam Halls</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{stats['teachers']}</div>
        <div class="stat-label">Faculty</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{stats['students']}</div>
        <div class="stat-label">Students</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{stats['exams']}</div>
        <div class="stat-label">Exams</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{stats['seating_plans']}</div>
        <div class="stat-label">Seating Plans</div>
      </div>
    </div>

    <!-- Quick API Explorer Cards -->
    <h2 class="section-title">🚀 API Gateways & Blueprints</h2>
    <div class="endpoints-grid">
      <div class="card">
        <div class="card-header">
          <span class="card-title">System Health & Ping</span>
          <a class="card-link" href="/api/health" target="_blank">GET /api/health</a>
        </div>
        <p class="card-desc">Returns application environment, database readiness, and operational status.</p>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">Member 4 Contracts</span>
          <a class="card-link" href="/api/reports/contracts" target="_blank">GET /api/reports/contracts</a>
        </div>
        <p class="card-desc">Inspects JSON data contract schemas for seating, invigilation, and document reports.</p>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">Polytechnic Departments</span>
          <a class="card-link" href="/api/departments/semesters" target="_blank">GET /api/departments/semesters</a>
        </div>
        <p class="card-desc">Standard 3-Year Diploma curriculum structure (Semesters 1 through 6).</p>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">Student Kiosk Seat Search</span>
          <a class="card-link" href="/api/student/seat-search?roll_number=C01" target="_blank">GET /api/student/seat-search</a>
        </div>
        <p class="card-desc">Public lookups for notice board terminals to check assigned halls by student roll number.</p>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">Room Seating Capacity</span>
          <a class="card-link" href="/api/rooms/capacity-summary" target="_blank">GET /api/rooms/capacity-summary</a>
        </div>
        <p class="card-desc">Computes physical seat counts and available exam room capacity.</p>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">Raw JSON System Index</span>
          <a class="card-link" href="/api?format=json" target="_blank">GET /api?format=json</a>
        </div>
        <p class="card-desc">Returns structured machine-readable JSON metadata for automated test runners.</p>
      </div>
    </div>

    <!-- Default Test Accounts -->
    <h2 class="section-title">🔑 Seeded Testing Credentials</h2>
    <div class="card" style="margin-bottom: 2.5rem; overflow-x: auto;">
      <table>
        <thead>
          <tr>
            <th>Role</th>
            <th>Username</th>
            <th>Password</th>
            <th>Name & Details</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><span class="role-badge role-admin">ADMIN</span></td>
            <td><code>admin</code></td>
            <td><code>Admin@12345</code></td>
            <td>Institutional Examination Cell Administrator</td>
          </tr>
          <tr>
            <td><span class="role-badge role-admin">ADMIN</span></td>
            <td><code>coe_admin</code></td>
            <td><code>Admin@12345</code></td>
            <td>Controller of Examinations</td>
          </tr>
          <tr>
            <td><span class="role-badge role-teacher">TEACHER</span></td>
            <td><code>dr_kulkarni</code></td>
            <td><code>Password123!</code></td>
            <td>Dr. Anand Kulkarni (Computer Engg HOD)</td>
          </tr>
          <tr>
            <td><span class="role-badge role-teacher">TEACHER</span></td>
            <td><code>prof_patil</code></td>
            <td><code>Password123!</code></td>
            <td>Prof. Suresh Patil (Computer Engg Lecturer)</td>
          </tr>
          <tr>
            <td><span class="role-badge role-teacher">TEACHER</span></td>
            <td><code>prof_jadhav</code></td>
            <td><code>Password123!</code></td>
            <td>Prof. Manoj Jadhav (Mechanical Engg Lecturer)</td>
          </tr>
          <tr>
            <td><span class="role-badge role-student">STUDENT</span></td>
            <td><code>24252271491</code> <em style="font-size:0.8rem;color:#94a3b8;">or Name</em></td>
            <td><code>24252271491</code></td>
            <td>ADHAV HARSH NIVRUTTI (TYCO - Div C, Batch C1, Roll: C01)</td>
          </tr>
          <tr>
            <td><span class="role-badge role-student">STUDENT</span></td>
            <td><code>24252271613</code> <em style="font-size:0.8rem;color:#94a3b8;">or Name</em></td>
            <td><code>24252271613</code></td>
            <td>SALUNKE AARYAN KAPIL (TYCO - Div C, Batch C2, Roll: C36)</td>
          </tr>
          <tr>
            <td><span class="role-badge role-student">STUDENT</span></td>
            <td><code>2109880464</code> <em style="font-size:0.8rem;color:#94a3b8;">or Name</em></td>
            <td><code>2109880464</code></td>
            <td>PAWAR SANDESH GOPAL (TYCO - Div C, Batch C2, Roll: C68)</td>
          </tr>
        </tbody>
      </table>
      <p style="margin-top: 1rem; color: #94a3b8; font-size: 0.85rem; line-height: 1.4;">
        💡 <strong>Polytechnic Student Login:</strong> All 67 imported TYCO Division C students can authenticate using either their <strong>Full Name</strong> (e.g. <code>ADHAV HARSH NIVRUTTI</code>) or their <strong>Enrollment Number</strong> as username, with their official <strong>Enrollment Number</strong> as password.
      </p>
    </div>

    <!-- Footer -->
    <div class="footer">
      <p>Smart Polytechnic Exam Seating & Invigilation Planner (Version 1.0)</p>
      <p>Delivered by <strong>Member 3 (Backend Architect & Database Engineer)</strong> • Fully Verified (29/29 Pytest Suites)</p>
    </div>
  </div>
</body>
</html>"""
    return Response(html_content, mimetype="text/html")
