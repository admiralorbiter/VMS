// Modal logic for attendance details editing

document.addEventListener('click', function(e) {
    if (e.target.classList.contains('edit-attendance-btn')) {
        e.preventDefault();
        const row = e.target.closest('tr');
        const eventId = row.dataset.eventId;
        openAttendanceDetailModal(eventId, row);
    }
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
                    <label for="total_students">Total Students:</label>
                    <input type="number" id="total_students" name="total_students" class="form-control" min="0">
                    <small class="form-text text-muted">Estimated total number of students who attended</small>
                </div>
                <div class="form-group">
                    <label for="num_classrooms">Number of Classrooms/Tables:</label>
                    <input type="number" id="num_classrooms" name="num_classrooms" class="form-control" min="0">
                    <small class="form-text text-muted">Number of classrooms or tables used for the event</small>
                </div>
                <div class="form-group">
                    <label for="rotations">Rotations:</label>
                    <input type="number" id="rotations" name="rotations" class="form-control" min="0">
                    <small class="form-text text-muted">Number of rotations for the event</small>
                </div>
                <div class="form-group">
                    <label for="students_per_volunteer">Students per Volunteer (Calculated):</label>
                    <input type="number" id="students_per_volunteer" name="students_per_volunteer" class="form-control" readonly>
                    <small class="form-text text-muted">Automatically calculated as: (Total Students / Classrooms) × Rotations</small>
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
    form.total_students.value = data.total_students || '';
    form.num_classrooms.value = data.num_classrooms || '';
    form.rotations.value = data.rotations || '';
    form.students_per_volunteer.value = data.students_per_volunteer || '';
    form.attendance_in_sf.checked = !!data.attendance_in_sf;
    form.pathway.value = data.pathway || '';
    form.groups_rotations.value = data.groups_rotations || '';
    form.is_stem.checked = !!data.is_stem;
    form.attendance_link.value = data.attendance_link || '';

    // Add event listeners for automatic calculation
    const calculateStudentsPerVolunteer = () => {
        const totalStudents = parseInt(form.total_students.value) || 0;
        const numClassrooms = parseInt(form.num_classrooms.value) || 0;
        const rotations = parseInt(form.rotations.value) || 0;

        if (totalStudents > 0 && numClassrooms > 0 && rotations > 0) {
            const calculated = Math.floor((totalStudents / numClassrooms) * rotations);
            form.students_per_volunteer.value = calculated;
        } else {
            form.students_per_volunteer.value = '';
        }
    };

    // Add event listeners to the calculation fields
    form.total_students.addEventListener('input', calculateStudentsPerVolunteer);
    form.num_classrooms.addEventListener('input', calculateStudentsPerVolunteer);
    form.rotations.addEventListener('input', calculateStudentsPerVolunteer);

    // Calculate initial value
    calculateStudentsPerVolunteer();

    // Submit logic
    form.onsubmit = function(e) {
        e.preventDefault();
        const payload = {
            total_students: form.total_students.value,
            num_classrooms: form.num_classrooms.value,
            rotations: form.rotations.value,
            students_per_volunteer: form.students_per_volunteer.value,
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
