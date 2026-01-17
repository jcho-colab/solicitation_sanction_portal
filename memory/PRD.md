# Automotive Parts Supplier Portal - Product Requirements Document

## Original Problem Statement
Build a comprehensive Automotive Parts Supplier Portal for managing parts, components, documents, and compliance data. The portal supports multiple user roles (Admin/Supplier) with BRP corporate branding.

## Core Features Implemented

### Authentication & Users
- JWT-based authentication with bcrypt password hashing
- Two user roles: Admin and Supplier
- Role-based access control

### Parts Management
- Parent SKUs with hierarchical child components
- CRUD operations for parts and components
- Status tracking (Completed, Incomplete, Needs Review)
- Country of Origin and Manufacturing Method dropdowns
- Click-to-expand parent rows to view children

### Document Management
- Document upload with file storage
- **Auto-apply to children**: When uploading a document to a parent SKU, it automatically applies to all child components
- **Document download**: Authenticated download from both Manage Documents modal and component-level icons
- **Document reassignment**: Multi-select functionality with Ctrl+Click, Shift+Click, and Select All button to reassign documents to different parts/components

### Data Import/Export
- Excel template download
- Bulk import from Excel files
- Export parts data to Excel

### Audit Logging
- Track all changes to parts, components, and documents
- Admin-only access to audit logs

## Technical Stack
- **Frontend**: React, TailwindCSS, shadcn/ui
- **Backend**: FastAPI, Python
- **Database**: MongoDB

## Key Files
- `/app/backend/server.py` - All backend API endpoints
- `/app/frontend/src/pages/SupplierDashboard.js` - Supplier dashboard with all CRUD operations
- `/app/frontend/src/pages/AdminDashboard.js` - Admin dashboard
- `/app/frontend/src/lib/api.js` - Frontend API client

## Test Credentials
- **Supplier**: supplier1@metalworks.com / supplier123
- **Admin**: admin@rvparts.com / admin123

## Completed Work (January 2025)

### Document Management Fixes
1. **Auto-apply documents to children**: When selecting a parent SKU in the Upload Document modal, all child components are automatically included
2. **Document download authentication**: All document downloads now use authenticated fetch requests
3. **Document reassignment feature**: 
   - Multi-select with Ctrl+Click, Shift+Click
   - Select All / Deselect All button
   - Reassign Selected button with modal
   - Choose new parent SKUs or specific components
   - Warning when no selection is made

## Backlog / Future Tasks

### P1 - High Priority
- Admin-side full CRUD for parts (including delete parent SKUs)
- Backend validation for Excel imports (country codes, manufacturing methods)

### P2 - Medium Priority
- Advanced Audit Log filtering (by user, entity, date range)
- UI refactoring: Break down SupplierDashboard.js into smaller components

### P3 - Nice to Have
- Email notifications for document uploads
- Dashboard analytics and charts
- Bulk document operations
