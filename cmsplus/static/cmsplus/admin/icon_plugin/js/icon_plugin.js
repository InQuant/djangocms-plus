document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".icon-field-widget").forEach(widget => {
    const selectedIconContainer = widget.querySelector(".highlight-selected-icon");
    const selectedIcon = widget.querySelector(".selected-icon");
    const selectedIconName = widget.querySelector(".selected-icon-name");
    const hiddenInput = widget.querySelector(".hidden-icon-field");
    const iconButtons = widget.querySelectorAll(".icon-select-btn");
    const iconSearch = widget.querySelector(".icon-search");

    const modalId = "iconSelectModal-" + widget.dataset.widgetId;
    const modalElement = document.getElementById(modalId);

    iconButtons.forEach(button => {
      button.addEventListener("click", function () {
        const iconClass = this.getAttribute("data-icon-class");
        const iconName = this.getAttribute("data-icon-name");

        selectedIcon.className = "selected-icon " + iconClass;
        selectedIconName.textContent = iconName;
        hiddenInput.value = iconClass;
        selectedIconContainer.style.display = "block";

        // Modal schließen (Bootstrap 5)
        const modalInstance = bootstrap.Modal.getInstance(modalElement);
        modalInstance.hide();
      });
    });

    iconSearch.addEventListener("input", function () {
      const filter = this.value.toLowerCase();
      iconButtons.forEach(button => {
        const name = button.getAttribute("data-icon-name").toLowerCase();
        button.style.display = name.includes(filter) ? "inline-block" : "none";
      });
    });
  });
});
