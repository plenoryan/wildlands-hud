(() => {
  const scene = document.querySelector('[data-scene]');
  const caption = document.querySelector('[data-scene-caption]');
  const controls = document.querySelectorAll('[data-mode-button]');
  if (!scene || !caption || !controls.length) return;
  controls.forEach(button => {
    button.addEventListener('click', () => {
      scene.dataset.mode = button.dataset.modeButton;
      controls.forEach(control => control.setAttribute('aria-pressed', String(control === button)));
      caption.textContent = button.dataset.caption;
    });
  });
})();
