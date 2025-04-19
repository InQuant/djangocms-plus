document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".icon-field-widget").forEach(widget => {
    const selectedIconContainer = widget.querySelector(".highlight-selected-icon");
    const selectedIcon = widget.querySelector(".selected-icon");
    const selectedIconName = widget.querySelector(".selected-icon-name");
    const hiddenInput = widget.querySelector(".hidden-icon-field");

    const modalId = "iconSelectModal-" + widget.dataset.widgetId;
    const modalElement = document.getElementById(modalId);

    const iconContainer = modalElement.querySelector(".icon-list");
    const iconSearch = modalElement.querySelector(".icon-search");
    const rawJson = iconContainer.dataset.iconsJson;
    const icons = JSON.parse(rawJson);

    let iconsLoaded = false;

    // Insert Icons during opening modal
    modalElement.addEventListener("show.bs.modal", function () {
      if (iconsLoaded) return;

      icons.forEach(icon => {
        const button = document.createElement("button");
        button.className = "btn btn-light icon-select-btn";
        button.setAttribute("type", "button");
        button.setAttribute("data-icon-name", icon.name);
        button.setAttribute("data-icon-class", icon.font_class_name);
        button.innerHTML = `<i class="${icon.font_class_name}"></i>`;

        button.addEventListener("click", function () {
          selectedIcon.className = "selected-icon " + icon.font_class_name;
          selectedIconName.textContent = icon.name;
          hiddenInput.value = icon.font_class_name;
          selectedIconContainer.style.display = "block";

          bootstrap.Modal.getInstance(modalElement).hide();
        });

        iconContainer.appendChild(button);
      });

      iconsLoaded = true;
    });

    // Search
    iconSearch.addEventListener("input", function () {
      const filter = this.value.toLowerCase();
      iconContainer.querySelectorAll(".icon-select-btn").forEach(button => {
        const name = button.getAttribute("data-icon-name").toLowerCase();
        button.style.display = name.includes(filter) ? "inline-block" : "none";
      });
    });
  });
});
