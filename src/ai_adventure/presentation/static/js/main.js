document.addEventListener("DOMContentLoaded", () => {
  const narration = document.getElementById("narration");
  if (narration) {
    narration.dataset.ready = "true";
  }

  initCreationWizard();
  initSelectableCards();
});

/**
 * One-question-at-a-time character creation flow.
 * Pure presentation — form fields and POST payload are unchanged.
 */
function initCreationWizard() {
  const form = document.getElementById("vn-form");
  if (!form) {
    return;
  }

  const steps = Array.from(form.querySelectorAll(".vn-step"));
  const progress = document.getElementById("vn-progress");
  const backBtn = document.getElementById("vn-back");
  const nextBtn = document.getElementById("vn-next");
  const submitBtn = document.getElementById("vn-submit");
  if (!steps.length || !nextBtn || !submitBtn) {
    return;
  }

  let index = firstIncompleteStep(steps);

  function paint() {
    steps.forEach((step, i) => {
      step.classList.toggle("is-active", i === index);
    });
    if (progress) {
      progress.querySelectorAll("span").forEach((dot, i) => {
        dot.classList.toggle("is-current", i === index);
        dot.classList.toggle("is-done", i < index);
      });
    }
    if (backBtn) {
      backBtn.hidden = index === 0;
    }
    const last = index === steps.length - 1;
    nextBtn.hidden = last;
    submitBtn.hidden = !last;
  }

  function validateCurrent() {
    const step = steps[index];
    const nameField = step.querySelector('input[name="character_name"]');
    if (nameField) {
      const value = nameField.value.trim();
      if (!value) {
        nameField.focus();
        return false;
      }
      nameField.value = value;
      return true;
    }
    const radioName = step.dataset.requiredRadio;
    if (radioName) {
      const checked = step.querySelector(`input[name="${radioName}"]:checked`);
      if (!checked) {
        const first = step.querySelector(`input[name="${radioName}"]`);
        if (first) {
          first.focus();
        }
        return false;
      }
    }
    return true;
  }

  nextBtn.addEventListener("click", () => {
    if (!validateCurrent()) {
      return;
    }
    if (index < steps.length - 1) {
      index += 1;
      paint();
      focusStep(steps[index]);
    }
  });

  if (backBtn) {
    backBtn.addEventListener("click", () => {
      if (index > 0) {
        index -= 1;
        paint();
        focusStep(steps[index]);
      }
    });
  }

  form.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }
    const target = event.target;
    if (target && target.tagName === "TEXTAREA") {
      return;
    }
    if (index < steps.length - 1) {
      event.preventDefault();
      nextBtn.click();
    }
  });

  paint();
}

function firstIncompleteStep(steps) {
  for (let i = 0; i < steps.length; i += 1) {
    const step = steps[i];
    const nameField = step.querySelector('input[name="character_name"]');
    if (nameField && !nameField.value.trim()) {
      return i;
    }
    const radioName = step.dataset.requiredRadio;
    if (radioName && !step.querySelector(`input[name="${radioName}"]:checked`)) {
      return i;
    }
  }
  return 0;
}

function focusStep(step) {
  const focusable = step.querySelector(
    "input:not([type='radio']), textarea, .answer-card, .bg-card"
  );
  if (focusable && typeof focusable.focus === "function") {
    focusable.focus({ preventScroll: true });
  }
}

/** Keep selected card styling in sync for :has()-less browsers. */
function initSelectableCards() {
  document.querySelectorAll(".bg-card, .answer-card").forEach((card) => {
    const input = card.querySelector('input[type="radio"]');
    if (!input) {
      return;
    }
    const sync = () => {
      const name = input.name;
      document.querySelectorAll(`input[name="${name}"]`).forEach((radio) => {
        const parent = radio.closest(".bg-card, .answer-card");
        if (parent) {
          parent.classList.toggle("is-selected", radio.checked);
        }
      });
    };
    input.addEventListener("change", sync);
    sync();
  });
}
