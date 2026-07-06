/* ==========================================================================
   LedgerClass — client-side behavior
   - Phone format validation on the student form
   - Bootstrap modal confirmation before deleting a student
   - Mobile sidebar toggle
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ---------------- Mobile sidebar toggle ---------------- */
    var sidebarToggle = document.getElementById('sidebarToggle');
    var sidebar = document.querySelector('.sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('open');
        });
    }

    /* ---------------- Student form: phone validation ---------------- */
    var studentForm = document.getElementById('studentForm');
    var phoneInput = document.getElementById('phoneInput');

    function isValidPhone(value) {
        // Accepts digits, spaces, +, - ; length between 7 and 15 digits
        var digitsOnly = value.replace(/[^0-9]/g, '');
        var allowedChars = /^[0-9+\-\s]+$/.test(value);
        return allowedChars && digitsOnly.length >= 7 && digitsOnly.length <= 15;
    }

    if (phoneInput) {
        phoneInput.addEventListener('input', function () {
            if (phoneInput.value.trim() === '' || isValidPhone(phoneInput.value)) {
                phoneInput.classList.remove('is-invalid');
            } else {
                phoneInput.classList.add('is-invalid');
            }
        });
    }

    if (studentForm) {
        studentForm.addEventListener('submit', function (event) {
            var valid = true;

            // Native "required" fields
            var requiredFields = studentForm.querySelectorAll('[required]');
            requiredFields.forEach(function (field) {
                if (!field.value || !field.value.toString().trim()) {
                    field.classList.add('is-invalid');
                    valid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            });

            // Phone-specific check
            if (phoneInput && phoneInput.value.trim() !== '' && !isValidPhone(phoneInput.value)) {
                phoneInput.classList.add('is-invalid');
                valid = false;
            }

            if (!valid) {
                event.preventDefault();
            }
        });
    }

    /* ---------------- Delete confirmation modal ---------------- */
    var deleteModalEl = document.getElementById('deleteModal');
    var deleteModal = deleteModalEl ? new bootstrap.Modal(deleteModalEl) : null;
    var deleteNameEl = document.getElementById('deleteStudentName');
    var confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    var pendingForm = null;

    document.querySelectorAll('.js-delete-trigger').forEach(function (btn) {
        btn.addEventListener('click', function () {
            pendingForm = btn.closest('.delete-form');
            var name = pendingForm ? pendingForm.getAttribute('data-name') : 'this student';
            if (deleteNameEl) {
                deleteNameEl.textContent = name;
            }
            if (deleteModal) {
                deleteModal.show();
            }
        });
    });

    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', function () {
            if (pendingForm) {
                pendingForm.submit();
            }
            if (deleteModal) {
                deleteModal.hide();
            }
        });
    }
});
