// Modal logic for attendance details editing

document.addEventListener('DOMContentLoaded', function() {
    // Delegate edit button clicks
    document.querySelectorAll('.attendance-details-table .btn-primary').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const row = btn.closest('tr');
            const eventId = row.dataset.eventId || row.getAttribute('data-event-id') || row.querySelector('td').dataset.eventId;
            openAttendanceDetailModal(eventId, row);
        });
    });
});

function openAttendanceDetailModal(eventId, row) {
    fetch(`/attendance/details/${eventId}/detail`)
        .then(res => res.json())
        .then(data => {
            showAttendanceDetailModal(eventId, data, row);
        });
}

function showAttendanceDetailModal(eventId, data, row) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('attendanceDetailModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'attendanceDetailModal';
        modal.className = 'modal';
        modal.style.display = 'none';
        modal.style.position = 'fixed';
        modal.style.zIndex = '1000';
        modal.style.left = '0';
        modal.style.top = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0,0,0,0.4)';
        
        const modalContent = document.createElement('div');
        modalContent.style.backgroundColor = '#fefefe';
        modalContent.style.margin = '5% auto';
        modalContent.style.padding = '20px';
        modalContent.style.border = '1px solid #888';
        modalContent.style.width = '80%';
        modalContent.style.maxWidth = '600px';
        modalContent.style.borderRadius = '5px';
        
        modalContent.innerHTML = `
            <h2>Edit Attendance Details</h2>
            <form id="attendanceDetailForm">
                <div class="form-group">
                    <label for="num_classrooms">Number of Classrooms/Tables:</label>
                    <input type="number" id="num_classrooms" name="num_classrooms" class="form-control">
                </div>
                <div class="form-group">
                    <label for="students_per_volunteer">Students per Volunteer:</label>
                    <input type="number" id="students_per_volunteer" name="students_per_volunteer" class="form-control">
                </div>
                <div class="form-group">
                    <label for="total_students">Total Students:</label>
                    <input type="number" id="total_students" name="total_students" class="form-control">
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="attendance_in_sf" name="attendance_in_sf">
                        Attendance in Salesforce
                    </label>
                </div>
                <div class="form-group">
                    <label for="pathway">Pathway:</label>
                    <input type="text" id="pathway" name="pathway" class="form-control">
                </div>
                <div class="form-group">
                    <label for="groups_rotations">Groups & Rotations:</label>
                    <input type="text" id="groups_rotations" name="groups_rotations" class="form-control">
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="is_stem" name="is_stem">
                        STEM Event
                    </label>
                </div>
                <div class="form-group">
                    <label for="attendance_link">Attendance Link:</label>
                    <input type="url" id="attendance_link" name="attendance_link" class="form-control">
                </div>
                <div class="form-group">
                    <button type="submit" class="btn btn-primary">Save</button>
                    <button type="button" class="btn btn-secondary" onclick="document.getElementById('attendanceDetailModal').style.display='none'">Cancel</button>
                </div>
            </form>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
    }
    
    // Populate form with data
    const form = document.getElementById('attendanceDetailForm');
    form.num_classrooms.value = data.num_classrooms || '';
    form.students_per_volunteer.value = data.students_per_volunteer || '';
    form.total_students.value = data.total_students || '';
    form.attendance_in_sf.checked = !!data.attendance_in_sf;
    form.pathway.value = data.pathway || '';
    form.groups_rotations.value = data.groups_rotations || '';
    form.is_stem.checked = !!data.is_stem;
    form.attendance_link.value = data.attendance_link || '';
    // Submit logic
    form.onsubmit = function(e) {
        e.preventDefault();
        const payload = {
            num_classrooms: form.num_classrooms.value,
            students_per_volunteer: form.students_per_volunteer.value,
            total_students: form.total_students.value,
            attendance_in_sf: form.attendance_in_sf.checked,
            pathway: form.pathway.value,
            groups_rotations: form.groups_rotations.value,
            is_stem: form.is_stem.checked,
            attendance_link: form.attendance_link.value
        };
        fetch(`/attendance/details/${eventId}/detail`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(resp => {
            if (resp.success) {
                modal.style.display = 'none';
                // Optionally update the row in the table
                location.reload(); // For now, reload to show changes
            } else {
                alert('Error saving attendance detail');
            }
        });
    };
    modal.style.display = 'block';
} 