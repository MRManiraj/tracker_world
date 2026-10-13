document.addEventListener("DOMContentLoaded", function () {

    const form = document.querySelector("form");
    const employeeId = document.querySelector(
        'input[name="employee_id"]'
    );
    const password = document.querySelector(
        'input[name="password"]'
    );

    if (form) {
        form.addEventListener("submit", function (event) {

            if (employeeId && employeeId.value.trim() === "") {
                event.preventDefault();
                alert("Please enter Employee ID");
                employeeId.focus();
                return;
            }

            if (password && password.value.trim() === "") {
                event.preventDefault();
                alert("Please enter Password");
                password.focus();
                return;
            }
        });
    }

});