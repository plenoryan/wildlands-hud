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

(() => {
  const button = document.querySelector('[data-copy-pix]');
  const key = document.querySelector('#pix-key');
  const status = document.querySelector('[data-copy-status]');
  if (!button || !key || !status) return;
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(key.value);
      status.textContent = button.dataset.copySuccess;
    } catch {
      key.focus();
      key.select();
      status.textContent = button.dataset.copyFailure;
    }
  });
})();
