# Virtual Event Management

This guide covers the lifecycle of virtual events in Polaris, including creation, presenter recruitment, and attendance tracking.

## 1. Creating Virtual Events

Virtual events are managed directly in Polaris (unlike In-Person events which sync from Salesforce).

1.  Navigate to **Virtual** in the main menu.
    ![Create Session Step 1](images/create_virtual_session_step1.png)
2.  Click **"New Session"**.
3.  Fill in details: Title, Date/Time, School, District.
    ![Create Session Step 2](images/create_virtual_session_step2.png)
4.  **Tag Teachers**: Search/select teachers to associate them with the event.
    ![Create Session Step 3](images/create_virtual_session_step3.png)
    *   **Quick Create**: If the teacher is not found, click **"Quick Create Teacher"**. Enter the First Name, Last Name, and School, then click **"Save & Add"**. The teacher will be created and added immediately. You can remove the blank search row if it is no longer needed.
    ![Quick Create Teacher](images/quick_create_teacher.png)
5.  **Tag Presenters**: Search/select volunteers acting as presenters.
    ![Create Session Step 4](images/create_virtual_session_step4.png)
    *   **Quick Create**: If the presenter is not found, click **"Quick Create Presenter"**. Enter the required details and click **"Save & Add"** to create and link them immediately.
6.  Click **"Create Session"**.

## 2. Presenter Recruitment

The **Presenter Recruitment View** helps identifying sessions that need volunteers.

-   **Access**: `Reports > Presenter Recruitment` (Admin/Global only).
-   **Status**:
    -   🔴 **Urgent**: ≤ 7 days.
    -   🟡 **Warning**: 8-14 days.
    -   🔵 **Normal**: > 14 days.
-   **Action**: Click an event to "Edit" and tag a presenter. Once a presenter is tagged, the event disappears from this list.

## 3. Importing Data

### Pathful Import (Recommended)

Polaris can ingest attendance data directly from Pathful exports. This is the primary method for importing virtual session data.

📖 **See the full guide:** [Pathful Import Guide](pathful_import)

**Quick Steps:**
1. Go to **Virtual → Pathful Imports**
2. Upload the Session Report (.xlsx)
3. System creates sessions and matches participants

> [!NOTE]
> The Pathful direct import replaces the old Google Sheets workflow. You no longer need to manually reformat data.

### Legacy: Historical Import (Deprecated)

> [!WARNING]
> The Google Sheets historical import is deprecated. Use Pathful direct import instead.

~~Import past data (2-4 years) from Google Sheets archives.~~

---

## Technical Scope & Traceability

This guide addresses the following scopes:

| Component | Items |
|---|---|
| **User Stories** | [US-301](user_stories#us-301), [US-302](user_stories#us-302), [US-303](user_stories#us-303), [US-304](user_stories#us-304), [US-306](user_stories#us-306), [US-307](user_stories#us-307) |
| **Requirements** | [FR-VIRTUAL-201](requirements#fr-virtual-201) through [FR-VIRTUAL-219](requirements#fr-virtual-219) |
