# Slalom Capabilities Management API

<p align="center">
  <img src="https://colby-timm.github.io/images/byte-teacher.png" alt="Byte Teacher" width="200" />
</p>

A FastAPI application that enables Slalom consultants to register their capabilities and manage consulting expertise across the organization.

## Features

- View all available consulting capabilities
- Secure sign-in for practice leads and consultants
- Register consultant expertise and availability with role-based workflows
- Track skill levels and certifications
- Manage capability capacity and team assignments
- Practice lead approval workflow for consultant self-registration requests
- Audit log API for capability changes (practice lead only)

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc
   - Capabilities Dashboard: http://localhost:8000/

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/capabilities`                                                   | Get all capabilities with details and current consultant assignments |
| POST   | `/auth/login`                                                     | Sign in and receive a bearer access token                           |
| GET    | `/auth/me`                                                        | Get current signed-in user profile                                  |
| POST   | `/capabilities/{capability_name}/register?email=consultant@slalom.com` | Practice lead direct register or consultant self-request            |
| POST   | `/capabilities/{capability_name}/approve?email=consultant@slalom.com` | Practice lead approval endpoint for pending requests                |
| DELETE | `/capabilities/{capability_name}/unregister?email=consultant@slalom.com` | Practice lead unregister endpoint                                  |
| GET    | `/audit-logs`                                                     | View capability audit trail (practice lead only)                    |

## Demo Credentials

Credentials are stored in `practice_leads.json` with salted password hashes.

- Practice lead: `tech.lead` / `LeadTech!2026`
- Consultant: `alex.consultant` / `Consultant!2026`

Use the "Sign In" button in the header to authenticate.

## Data Model

The application uses a consulting-focused data model:

1. **Capabilities** - Uses capability name as identifier:
   - Description of the consulting capability
   - Skill levels (Emerging, Proficient, Advanced, Expert)
   - Practice area (Strategy, Technology, Operations)
   - Industry verticals served
   - Required certifications
   - List of consultant emails registered
   - Available capacity (hours per week)
   - Geographic location preferences

2. **Consultants** - Uses email as identifier:
   - Name
   - Practice area
   - Skill level
   - Certifications
   - Availability

All data is currently stored in memory for this learning exercise. In a production environment, this would be backed by a robust database system.

## Future Enhancements

This exercise will guide you through implementing:
- Capability maturity assessments
- Intelligent team matching algorithms  
- Analytics dashboards for practice leads
- Integration with project management systems
- Advanced search and filtering capabilities
