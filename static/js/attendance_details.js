// Modal logic for attendance impact editing

document.addEventListener('DOMContentLoaded', function() {
    // Delegate edit button clicks
    document.querySelectorAll('.attendance-impact-table .btn-primary').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const row = btn.closest('tr');
            const eventId = row.dataset.eventId || row.getAttribute('data-event-id') || row.querySelector('td').dataset.eventId;
            openAttendanceDetailModal(eventId, row);
        });
    });
});

function openAttendanceDetailModal(eventId, row) {
    fetch(`/attendance/impact/${eventId}/detail`)
        .then(res => res.json())
        .then(data => {
            showAttendanceDetailModal(eventId, data, row);
        });
}

function showAttendanceDetailModal(eventId, data, row) {
    // Create modal if not exists
    let modal = document.getElementById('attendanceDetailModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'attendanceDetailModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <span class="close">&times;</span>
                <h2>Edit Attendance Detail</h2>
                <form id="attendanceDetailForm">
                    <label>No. of Classrooms/Tables: <input type="number" name="num_classrooms"></label><br>
                    <label>Students per Volunteer: <input type="number" name="students_per_volunteer"></label><br>
                    <label>Total Students: <input type="number" name="total_students"></label><br>
                    <label>Attendance in SF: <input type="checkbox" name="attendance_in_sf"></label><br>
                    <label>Pathway: <input type="text" name="pathway"></label><br>
                    <label>Groups & Rotations: <input type="text" name="groups_rotations"></label><br>
                    <label>STEM: <input type="checkbox" name="is_stem"></label><br>
                    <label>Attendance Link: <input type="text" name="attendance_link"></label><br>
                    <button type="submit">Save</button>
                </form>
            </div>
        `;
        document.body.appendChild(modal);
        // Close logic
        modal.querySelector('.close').onclick = function() {
            modal.style.display = 'none';
        };
        window.onclick = function(event) {
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        };
    }
    // Fill form
    const form = modal.querySelector('#attendanceDetailForm');
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
        fetch(`/attendance/impact/${eventId}/detail`, {
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