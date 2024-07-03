document.addEventListener("DOMContentLoaded", function () {
    const sidebar = document.getElementById("sidebar");
    const sidebarHeader = document.querySelector("#sidebar .sidebar-header");
    const sidebarItems = document.querySelectorAll("#sidebar ul li");

    // Function to set initial active state based on current URL
    function setActiveSidebarItem() {
        const currentPath = window.location.pathname;
        sidebarItems.forEach(function (item) {
            const link = item.querySelector('a');
            if (link && link.getAttribute('href') === currentPath) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });
    }

    // Set active sidebar item on page load
    setActiveSidebarItem();

    // Toggle sidebar when clicking on header
    sidebarHeader.addEventListener("click", function () {
        sidebar.classList.toggle("collapsed");
    });

    // Handle clicks on sidebar items
    sidebarItems.forEach(function (item) {
        item.addEventListener("click", function () {
            // Remove active class from all sidebar items
            sidebarItems.forEach(function (sidebarItem) {
                sidebarItem.classList.remove("active");
            });

            // Add active class to the clicked item
            this.classList.add("active");
        });
    });
});