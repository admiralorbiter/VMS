# Email System Management

The **Email System** is a safe-by-default, testable email subsystem integrated into the VMS admin panel. It provides comprehensive email management capabilities with strong safeguards against accidental delivery.

## System Overview

- **Location**: `Management > Email`
- **Primary Use**: Sending consistent, branded communications to volunteers and stakeholders.
- **Key Feature**: "Two-Phase Sending" (Draft -> Queued -> Sent) preventing accidental blasts.

## Core Features

### 1. Templates
Manage versioned email templates ensuring consistency.
- **View Templates**: Go to `Management > Email > Templates`.
- **Preview**: See how emails will look with sample data before sending.

### 2. Outbox & Sending
All emails start in the **Outbox**.
- **Draft**: Message created but not ready.
- **Queued**: Ready for delivery.
- **Sent**: Successfully handed off to Mailjet.
- **Failed**: Delivery failed (see Attempts).

### 3. Safety Gates
- **Non-Production**: Emails are **blocked** unless the recipient is on the Allowlist.
- **Global Kill-Switch**: Delivery can be disabled globally by key environment variables.

## User Guide

### How to Monitor Delivery
1.  Navigate to **Email Dashboard** (`/management/email`).
2.  Check the **Health Metrics** (Queue size, Failures).
3.  Click **Delivery Attempts** to see detailed logs of every send attempt.

### How to Troubleshoot Failures
1.  Go to **Delivery Attempts**.
2.  Look for red "Failed" status.
3.  Click details to see the error from Mailjet (e.g., "bounced", "spam block").

## Technical Scope & Traceability

This guide addresses the following scopes:

| Component | Items |
|---|---|
| **User Stories** | [US-801](user_stories#us-801), [US-802](user_stories#us-802), [US-803](user_stories#us-803) |
| **Requirements** | [FR-EMAIL-801](requirements#fr-email-801), [FR-EMAIL-802](requirements#fr-email-802), [FR-EMAIL-803](requirements#fr-email-803), [FR-EMAIL-804](requirements#fr-email-804) |
