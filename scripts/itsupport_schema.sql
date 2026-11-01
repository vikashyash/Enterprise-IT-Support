-- Snapshot of schema itsupport from the live database.
-- Generated for reference. This file is not applied by the app.
-- It lists enums, tables, columns, keys, foreign keys and indexes.

CREATE SCHEMA IF NOT EXISTS itsupport;

-- Enums
CREATE TYPE itsupport.access_request_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'COMPLETED', 'CANCELLED');
CREATE TYPE itsupport.agent_run_status AS ENUM ('RUNNING', 'WAITING_APPROVAL', 'WAITING_USER', 'COMPLETED', 'FAILED', 'CANCELLED');
CREATE TYPE itsupport.approval_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED', 'CANCELLED');
CREATE TYPE itsupport.author_type AS ENUM ('EMPLOYEE', 'AGENT', 'SYSTEM', 'IT_AGENT');
CREATE TYPE itsupport.device_status AS ENUM ('ACTIVE', 'INACTIVE', 'IN_REPAIR', 'RETIRED', 'LOST');
CREATE TYPE itsupport.device_type AS ENUM ('LAPTOP', 'DESKTOP', 'MOBILE', 'TABLET', 'OTHER');
CREATE TYPE itsupport.employee_status AS ENUM ('ACTIVE', 'INACTIVE', 'ON_LEAVE', 'TERMINATED');
CREATE TYPE itsupport.incident_severity AS ENUM ('SEV1', 'SEV2', 'SEV3', 'SEV4');
CREATE TYPE itsupport.incident_status AS ENUM ('INVESTIGATING', 'IDENTIFIED', 'MONITORING', 'RESOLVED');
CREATE TYPE itsupport.install_status AS ENUM ('INSTALLED', 'PENDING', 'FAILED', 'UNINSTALLED');
CREATE TYPE itsupport.permission_status AS ENUM ('ACTIVE', 'REVOKED', 'EXPIRED', 'PENDING');
CREATE TYPE itsupport.service_status AS ENUM ('OPERATIONAL', 'DEGRADED', 'PARTIAL_OUTAGE', 'MAJOR_OUTAGE', 'MAINTENANCE');
CREATE TYPE itsupport.service_type AS ENUM ('NETWORK', 'IDENTITY', 'COLLABORATION', 'DEVELOPMENT', 'STORAGE', 'SECURITY', 'OTHER');
CREATE TYPE itsupport.software_category AS ENUM ('PRODUCTIVITY', 'DEVELOPMENT', 'SECURITY', 'COMMUNICATION', 'UTILITIES', 'OTHER');
CREATE TYPE itsupport.ticket_priority AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE itsupport.ticket_status AS ENUM ('OPEN', 'IN_PROGRESS', 'WAITING_ON_USER', 'WAITING_ON_APPROVAL', 'RESOLVED', 'CLOSED', 'CANCELLED');
CREATE TYPE itsupport.user_role AS ENUM ('EMPLOYEE', 'IT_AGENT', 'IT_ADMIN', 'SECURITY_ADMIN', 'MANAGER');

-- access_requests
CREATE TABLE itsupport.access_requests (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.access_requests_id_seq'::regclass),
    company_id BIGINT NOT NULL,
    employee_id BIGINT NOT NULL,
    resource VARCHAR(255) NOT NULL,
    requested_role VARCHAR(64) NOT NULL,
    reason TEXT NOT NULL,
    status itsupport.access_request_status NOT NULL DEFAULT 'PENDING'::itsupport.access_request_status,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_by BIGINT NULL,
    approved_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    idempotency_key VARCHAR(128) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT access_requests_company_id_idempotency_key_key UNIQUE (company_id, idempotency_key),
    CONSTRAINT access_requests_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES itsupport.employees (id),
    CONSTRAINT access_requests_company_id_fkey FOREIGN KEY (company_id) REFERENCES itsupport.companies (id),
    CONSTRAINT access_requests_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES itsupport.employees (id)
);

CREATE INDEX idx_access_requests_employee ON itsupport.access_requests USING btree (employee_id);
CREATE INDEX idx_access_requests_status ON itsupport.access_requests USING btree (status);

-- agent_executions
CREATE TABLE itsupport.agent_executions (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.agent_executions_id_seq'::regclass),
    company_id BIGINT NOT NULL,
    run_id VARCHAR(64) NOT NULL,
    conversation_id VARCHAR(64) NOT NULL,
    user_id BIGINT NOT NULL,
    status itsupport.agent_run_status NOT NULL DEFAULT 'RUNNING'::itsupport.agent_run_status,
    model VARCHAR(128) NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    tool_calls INTEGER NOT NULL DEFAULT 0,
    tool_failures INTEGER NOT NULL DEFAULT 0,
    final_status VARCHAR(64) NULL,
    error_summary TEXT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT agent_executions_company_id_run_id_key UNIQUE (company_id, run_id),
    CONSTRAINT agent_executions_company_id_fkey FOREIGN KEY (company_id) REFERENCES itsupport.companies (id),
    CONSTRAINT agent_executions_user_id_fkey FOREIGN KEY (user_id) REFERENCES itsupport.employees (id)
);

CREATE INDEX idx_agent_exec_conversation ON itsupport.agent_executions USING btree (conversation_id);

-- approval_requests
CREATE TABLE itsupport.approval_requests (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.approval_requests_id_seq'::regclass),
    company_id BIGINT NOT NULL,
    conversation_id VARCHAR(64) NULL,
    agent_run_id VARCHAR(64) NULL,
    requester_id BIGINT NOT NULL,
    approver_id BIGINT NULL,
    action_type VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    resource_id VARCHAR(128) NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    reason TEXT NULL,
    status itsupport.approval_status NOT NULL DEFAULT 'PENDING'::itsupport.approval_status,
    decided_at TIMESTAMPTZ NULL,
    decision_note TEXT NULL,
    expires_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT approval_requests_approver_id_fkey FOREIGN KEY (approver_id) REFERENCES itsupport.employees (id),
    CONSTRAINT approval_requests_company_id_fkey FOREIGN KEY (company_id) REFERENCES itsupport.companies (id),
    CONSTRAINT approval_requests_requester_id_fkey FOREIGN KEY (requester_id) REFERENCES itsupport.employees (id)
);

CREATE INDEX idx_approvals_requester ON itsupport.approval_requests USING btree (requester_id);
CREATE INDEX idx_approvals_status ON itsupport.approval_requests USING btree (status);

-- audit_logs
CREATE TABLE itsupport.audit_logs (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.audit_logs_id_seq'::regclass),
    company_id BIGINT NOT NULL,
    user_id BIGINT NULL,
    agent_run_id VARCHAR(64) NULL,
    conversation_id VARCHAR(64) NULL,
    action VARCHAR(128) NOT NULL,
    resource_type VARCHAR(64) NULL,
    resource_id VARCHAR(128) NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    result VARCHAR(32) NOT NULL DEFAULT 'SUCCESS'::character varying,
    ip_address INET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT audit_logs_company_id_fkey FOREIGN KEY (company_id) REFERENCES itsupport.companies (id),
    CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES itsupport.employees (id)
);

CREATE INDEX idx_audit_created ON itsupport.audit_logs USING btree (created_at DESC);
CREATE INDEX idx_audit_run ON itsupport.audit_logs USING btree (agent_run_id);
CREATE INDEX idx_audit_user ON itsupport.audit_logs USING btree (user_id);

-- companies
CREATE TABLE itsupport.companies (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.companies_id_seq'::regclass),
    code VARCHAR(32) NOT NULL,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT companies_code_key UNIQUE (code)
);

-- departments
CREATE TABLE itsupport.departments (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.departments_id_seq'::regclass),
    company_id BIGINT NOT NULL,
    name VARCHAR(128) NOT NULL,
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT departments_company_id_name_key UNIQUE (company_id, name),
    CONSTRAINT departments_company_id_fkey FOREIGN KEY (company_id) REFERENCES itsupport.companies (id)
);

-- devices
CREATE TABLE itsupport.devices (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.devices_id_seq'::regclass),
    company_id BIGINT NOT NULL,
    employee_id BIGINT NULL,
    asset_tag VARCHAR(64) NOT NULL,
    hostname VARCHAR(128) NOT NULL,
    device_type itsupport.device_type NOT NULL DEFAULT 'LAPTOP'::itsupport.device_type,
    manufacturer VARCHAR(64) NULL,
    model VARCHAR(128) NULL,
    operating_system VARCHAR(64) NOT NULL,
    os_version VARCHAR(64) NULL,
    cpu VARCHAR(128) NULL,
    ram_gb INTEGER NULL,
    storage_total_gb INTEGER NULL,
    storage_free_gb INTEGER NULL,
    ip_address INET NULL,
    mac_address MACADDR NULL,
    last_seen_at TIMESTAMPTZ NULL,
    status itsupport.device_status NOT NULL DEFAULT 'ACTIVE'::itsupport.device_status,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT devices_company_id_asset_tag_key UNIQUE (company_id, asset_tag),
    CONSTRAINT devices_company_id_hostname_key UNIQUE (company_id, hostname),
    CONSTRAINT devices_company_id_fkey FOREIGN KEY (company_id) REFERENCES itsupport.companies (id),
    CONSTRAINT devices_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES itsupport.employees (id)
);

CREATE INDEX idx_devices_employee ON itsupport.devices USING btree (employee_id);
CREATE INDEX idx_devices_status ON itsupport.devices USING btree (status);

-- employees
CREATE TABLE itsupport.employees (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.employees_id_seq'::regclass),
    company_id BIGINT NOT NULL,
    department_id BIGINT NOT NULL,
    manager_id BIGINT NULL,
    employee_code VARCHAR(32) NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    job_title VARCHAR(128) NOT NULL,
    role itsupport.user_role NOT NULL DEFAULT 'EMPLOYEE'::itsupport.user_role,
    status itsupport.employee_status NOT NULL DEFAULT 'ACTIVE'::itsupport.employee_status,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT employees_company_id_email_key UNIQUE (company_id, email),
    CONSTRAINT employees_company_id_employee_code_key UNIQUE (company_id, employee_code),
    CONSTRAINT employees_company_id_fkey FOREIGN KEY (company_id) REFERENCES itsupport.companies (id),
    CONSTRAINT employees_department_id_fkey FOREIGN KEY (department_id) REFERENCES itsupport.departments (id),
    CONSTRAINT employees_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES itsupport.employees (id)
);

CREATE INDEX idx_employees_dept ON itsupport.employees USING btree (department_id);
CREATE INDEX idx_employees_manager ON itsupport.employees USING btree (manager_id);
CREATE INDEX idx_employees_status ON itsupport.employees USING btree (status);

-- incidents
CREATE TABLE itsupport.incidents (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.incidents_id_seq'::regclass),
    company_id BIGINT NOT NULL,
    incident_number VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    affected_service_id BIGINT NULL,
    severity itsupport.incident_severity NOT NULL,
    status itsupport.incident_status NOT NULL DEFAULT 'INVESTIGATING'::itsupport.incident_status,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT incidents_company_id_incident_number_key UNIQUE (company_id, incident_number),
    CONSTRAINT incidents_affected_service_id_fkey FOREIGN KEY (affected_service_id) REFERENCES itsupport.services (id),
    CONSTRAINT incidents_company_id_fkey FOREIGN KEY (company_id) REFERENCES itsupport.companies (id)
);

CREATE INDEX idx_incidents_service ON itsupport.incidents USING btree (affected_service_id);
CREATE INDEX idx_incidents_status ON itsupport.incidents USING btree (status);

-- installed_software
CREATE TABLE itsupport.installed_software (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.installed_software_id_seq'::regclass),
    device_id BIGINT NOT NULL,
    software_id BIGINT NOT NULL,
    version VARCHAR(64) NOT NULL,
    installed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status itsupport.install_status NOT NULL DEFAULT 'INSTALLED'::itsupport.install_status,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT installed_software_device_id_software_id_key UNIQUE (device_id, software_id),
    CONSTRAINT installed_software_device_id_fkey FOREIGN KEY (device_id) REFERENCES itsupport.devices (id) ON DELETE CASCADE,
    CONSTRAINT installed_software_software_id_fkey FOREIGN KEY (software_id) REFERENCES itsupport.software (id)
);

CREATE INDEX idx_installed_software_device ON itsupport.installed_software USING btree (device_id);

-- knowledge_chunks
CREATE TABLE itsupport.knowledge_chunks (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.knowledge_chunks_id_seq'::regclass),
    document_id BIGINT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    content_hash VARCHAR(64) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT knowledge_chunks_document_id_chunk_index_key UNIQUE (document_id, chunk_index)
);

CREATE INDEX knowledge_chunks_embedding_hnsw ON itsupport.knowledge_chunks USING hnsw (embedding vector_cosine_ops);

-- knowledge_documents
CREATE TABLE itsupport.knowledge_documents (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.knowledge_documents_id_seq'::regclass),
    company_id BIGINT NULL,
    document_key VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL,
    department VARCHAR(128) NULL,
    version VARCHAR(32) NOT NULL,
    effective_date DATE NULL,
    source VARCHAR(255) NOT NULL,
    access_level VARCHAR(32) NOT NULL,
    access_rank SMALLINT NOT NULL DEFAULT 0,
    file_path TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    embedding_model VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX knowledge_documents_document_key_uidx ON itsupport.knowledge_documents (document_key);

-- permissions
CREATE TABLE itsupport.permissions (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.permissions_id_seq'::regclass),
    company_id BIGINT NOT NULL,
    employee_id BIGINT NOT NULL,
    resource VARCHAR(255) NOT NULL,
    role VARCHAR(64) NOT NULL,
    status itsupport.permission_status NOT NULL DEFAULT 'ACTIVE'::itsupport.permission_status,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ NULL,
    granted_by BIGINT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT permissions_company_id_employee_id_resource_role_key UNIQUE (company_id, employee_id, resource, role),
    CONSTRAINT permissions_company_id_fkey FOREIGN KEY (company_id) REFERENCES itsupport.companies (id),
    CONSTRAINT permissions_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES itsupport.employees (id),
    CONSTRAINT permissions_granted_by_fkey FOREIGN KEY (granted_by) REFERENCES itsupport.employees (id)
);

CREATE INDEX idx_permissions_employee ON itsupport.permissions USING btree (employee_id);

-- services
CREATE TABLE itsupport.services (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.services_id_seq'::regclass),
    company_id BIGINT NOT NULL,
    name VARCHAR(128) NOT NULL,
    service_type itsupport.service_type NOT NULL,
    status itsupport.service_status NOT NULL DEFAULT 'OPERATIONAL'::itsupport.service_status,
    health VARCHAR(32) NOT NULL DEFAULT 'HEALTHY'::character varying,
    description TEXT NULL,
    last_checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT services_company_id_name_key UNIQUE (company_id, name),
    CONSTRAINT services_company_id_fkey FOREIGN KEY (company_id) REFERENCES itsupport.companies (id)
);

-- software
CREATE TABLE itsupport.software (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.software_id_seq'::regclass),
    company_id BIGINT NOT NULL,
    name VARCHAR(128) NOT NULL,
    vendor VARCHAR(128) NULL,
    latest_version VARCHAR(64) NULL,
    license_required BOOLEAN NOT NULL DEFAULT false,
    approval_required BOOLEAN NOT NULL DEFAULT false,
    installation_allowed BOOLEAN NOT NULL DEFAULT true,
    category itsupport.software_category NOT NULL DEFAULT 'OTHER'::itsupport.software_category,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT software_company_id_name_key UNIQUE (company_id, name),
    CONSTRAINT software_company_id_fkey FOREIGN KEY (company_id) REFERENCES itsupport.companies (id)
);

-- ticket_comments
CREATE TABLE itsupport.ticket_comments (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.ticket_comments_id_seq'::regclass),
    ticket_id BIGINT NOT NULL,
    author_type itsupport.author_type NOT NULL,
    author_id BIGINT NULL,
    comment TEXT NOT NULL,
    is_internal BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    CONSTRAINT ticket_comments_ticket_id_fkey FOREIGN KEY (ticket_id) REFERENCES itsupport.tickets (id) ON DELETE CASCADE
);

CREATE INDEX idx_ticket_comments_ticket ON itsupport.ticket_comments USING btree (ticket_id);

-- tickets
CREATE TABLE itsupport.tickets (
    id BIGINT NOT NULL DEFAULT nextval('itsupport.tickets_id_seq'::regclass),
    company_id BIGINT NOT NULL,
    employee_id BIGINT NOT NULL,
    ticket_number VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(64) NOT NULL,
    subcategory VARCHAR(64) NULL,
    priority itsupport.ticket_priority NOT NULL DEFAULT 'MEDIUM'::itsupport.ticket_priority,
    status itsupport.ticket_status NOT NULL DEFAULT 'OPEN'::itsupport.ticket_status,
    assigned_team VARCHAR(64) NULL,
    assigned_to BIGINT NULL,
    related_device_id BIGINT NULL,
    related_service_id BIGINT NULL,
    idempotency_key VARCHAR(128) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ NULL,
    PRIMARY KEY (id),
    CONSTRAINT tickets_company_id_idempotency_key_key UNIQUE (company_id, idempotency_key),
    CONSTRAINT tickets_company_id_ticket_number_key UNIQUE (company_id, ticket_number),
    CONSTRAINT tickets_assigned_to_fkey FOREIGN KEY (assigned_to) REFERENCES itsupport.employees (id),
    CONSTRAINT tickets_company_id_fkey FOREIGN KEY (company_id) REFERENCES itsupport.companies (id),
    CONSTRAINT tickets_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES itsupport.employees (id),
    CONSTRAINT tickets_related_device_id_fkey FOREIGN KEY (related_device_id) REFERENCES itsupport.devices (id),
    CONSTRAINT tickets_related_service_id_fkey FOREIGN KEY (related_service_id) REFERENCES itsupport.services (id)
);

CREATE INDEX idx_tickets_created ON itsupport.tickets USING btree (created_at DESC);
CREATE INDEX idx_tickets_employee ON itsupport.tickets USING btree (employee_id);
CREATE INDEX idx_tickets_status ON itsupport.tickets USING btree (status);
