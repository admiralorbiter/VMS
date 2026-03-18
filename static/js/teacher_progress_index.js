function toggleSchoolDetail(schoolId) {
        const detailElement = document.getElementById('school-detail-' + schoolId);
        if (detailElement.style.display === 'none' || detailElement.style.display === '') {
            // Hide all other detail views
            const allDetails = document.querySelectorAll('.school-detail');
            allDetails.forEach(detail => {
                detail.style.display = 'none';
            });

            // Show the selected detail view
            detailElement.style.display = 'block';

            // Reset filter to "All" when opening a school detail
            const filterSelect = document.getElementById('filter-' + schoolId);
            if (filterSelect) {
                filterSelect.value = 'all';
                filterTeachersByStatus(schoolId, 'all');
            }

            // Scroll to the detail view
            detailElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
            // Hide the detail view
            detailElement.style.display = 'none';
        }
    }

    function filterTeachersByStatus(schoolId, status) {
        const teacherList = document.getElementById('teacher-list-' + schoolId);
        if (!teacherList) return;

        const teacherItems = teacherList.querySelectorAll('.teacher-item');

        teacherItems.forEach(item => {
            const itemStatus = item.getAttribute('data-status');

            if (status === 'all') {
                item.style.display = '';
            } else if (itemStatus === status) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });

        // Update count display if needed
        const visibleCount = Array.from(teacherItems).filter(item => item.style.display !== 'none').length;
        const totalCount = teacherItems.length;
    }
