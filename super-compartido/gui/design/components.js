/* Trick SDK component behaviors v1. Classic script; independent of app data.
   Provides input modality, PacoControls, PacoHaptics and PacoSheets. */
/* Shared input modality. Safe to include alongside existing catalog handlers. */
(() => {
  const root = document.documentElement;
  if (root.dataset.pacoInputReady) return;
  root.dataset.pacoInputReady = 'true';
  document.addEventListener('keydown', event => {
    if (!event.metaKey && !event.ctrlKey && !event.altKey) root.dataset.inputModality = 'keyboard';
  }, true);
  document.addEventListener('pointerdown', () => { root.dataset.inputModality = 'pointer'; }, true);
})();

/* DOM behavior adapters, independent of app data and APIs. Classic script for
   file-openable catalogs and standalone tricks. Call the returned cleanup. */
(() => {
  function combobox(input, list, { optionSelector, onSelect, onDismiss, dismissOnTab = true }) {
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-controls', list.id);
    list.setAttribute('role', 'listbox');
    const options = () => [...list.querySelectorAll(optionSelector)];
    const sync = () => {
      input.setAttribute('aria-expanded', String(list.classList.contains('open')));
      const activeId = input.getAttribute('aria-activedescendant');
      options().forEach((option, i) => {
        option.id = list.id + '-option-' + i;
        option.setAttribute('role', 'option');
        option.setAttribute('aria-selected', String(activeId ? option.id === activeId : option.classList.contains('active')));
      });
    };
    const observer = new MutationObserver(records => {
      if (records.some(record => record.type === 'childList')) input.removeAttribute('aria-activedescendant');
      sync();
    });
    observer.observe(list, { childList: true, attributes: true, attributeFilter: ['class'] });
    const keydown = event => {
      if (!list.classList.contains('open')) return;
      if (event.key === 'Escape' || (event.key === 'Tab' && dismissOnTab)) {
        if (event.key === 'Escape') event.preventDefault();
        input.removeAttribute('aria-activedescendant'); onDismiss(); return;
      }
      const items = options();
      if (!items.length) return;
      let index = items.findIndex(option => option.id === input.getAttribute('aria-activedescendant'));
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        index = index < 0 ? (event.key === 'ArrowDown' ? 0 : items.length - 1)
          : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
        input.setAttribute('aria-activedescendant', items[index].id);
        sync(); items[index].scrollIntoView({ block: 'nearest' });
      } else if (event.key === 'Enter' && index >= 0) {
        event.preventDefault(); onSelect(items[index]); input.removeAttribute('aria-activedescendant');
      }
    };
    input.addEventListener('keydown', keydown);
    sync();
    return () => { observer.disconnect(); input.removeEventListener('keydown', keydown); };
  }
  // For legacy overlays controlled by `hidden`. Prefer native <dialog>
  // showModal() for new overlays so the browser owns the top layer and focus.
  function dialogFocus(container, background) {
    const document = container.ownerDocument;
    let returnFocus, previous = [], wasOpen = !container.hidden;
    const observer = new MutationObserver(() => {
      const open = !container.hidden;
      if (open === wasOpen) return;
      wasOpen = open;
      if (open) {
        returnFocus = document.activeElement;
        previous = background.map(el => [el, el.inert]);
        background.forEach(el => { el.inert = true; });
      } else {
        previous.forEach(([el, inert]) => { el.inert = inert; });
        previous = [];
        if (returnFocus?.isConnected) returnFocus.focus();
      }
    });
    observer.observe(container, { attributes: true, attributeFilter: ['hidden'] });
    const keydown = event => {
      if (container.hidden || event.key !== 'Tab') return;
      const buttons = [...container.querySelectorAll('button:not(:disabled):not([hidden]),input:not(:disabled),a[href]')];
      if (!buttons.length) { event.preventDefault(); return; }
      const first = buttons[0], last = buttons.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', keydown);
    return () => { observer.disconnect(); document.removeEventListener('keydown', keydown); previous.forEach(([el, inert]) => { el.inert = inert; }); };
  }
  // A modal search picker: anchored on desktop, a bottom sheet on phones.
  // The native dialog owns focus containment and background inertness.
  function picker(trigger, dialog, { input, onDismiss }) {
    const viewport = window.visualViewport;
    const position = () => {
      const rect = trigger.getBoundingClientRect();
      const height = viewport?.height || window.innerHeight;
      const top = viewport?.offsetTop || 0;
      const width = Math.min(360, window.innerWidth - 32);
      const available = Math.max(180, height - 32);
      const panelHeight = Math.min(440, available);
      const y = Math.max(top + 16, Math.min(rect.bottom + 8, top + height - panelHeight - 16));
      dialog.style.setProperty('--picker-left', Math.max(16, Math.min(rect.right - width, window.innerWidth - width - 16)) + 'px');
      dialog.style.setProperty('--picker-top', y + 'px');
      dialog.style.setProperty('--picker-height', panelHeight + 'px');
      dialog.style.setProperty('--picker-viewport-bottom', Math.max(0, window.innerHeight - height - top) + 'px');
    };
    const close = () => {
      if (!dialog.open) return;
      dialog.close();
      trigger.setAttribute('aria-expanded', 'false');
      window.removeEventListener('resize', position);
      viewport?.removeEventListener('resize', position);
      viewport?.removeEventListener('scroll', position);
      onDismiss();
      if (trigger.isConnected) trigger.focus();
    };
    trigger.addEventListener('click', () => {
      position(); dialog.showModal(); trigger.setAttribute('aria-expanded', 'true');
      window.addEventListener('resize', position);
      viewport?.addEventListener('resize', position);
      viewport?.addEventListener('scroll', position);
      input.focus(); input.select();
    });
    dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
    dialog.querySelector('[data-picker-close]').addEventListener('click', close);
    dialog.addEventListener('click', event => { if (event.target === dialog) close(); });
    return { close };
  }
  window.PacoControls = { combobox, dialogFocus, picker };
})();

/* PACO press feedback. The app host owns native capabilities; tricks do not. */
(() => {
  if (window.PacoHaptics) return;
  const press = () => {
    if (window.parent === window) return;
    window.parent.postMessage({ type: 'paco:haptic', feedback: 'press' }, '*');
  };
  window.PacoHaptics = { press };
  // Capture before an async action disables its button. Never delay the action.
  document.addEventListener('click', event => {
    const button = event.target.closest?.('button[data-paco-haptic="press"]');
    if (!button || button.disabled || button.getAttribute('aria-disabled') === 'true') return;
    press();
  }, true);
})();

/* Native sheet behavior shared by the catalog and trick documents. */
(() => {
const openSheets = new Set();
let previousOverflow = '';
window.PacoSheets = {
  bind(dialog, { canDismiss = () => true } = {}) {
    let opener;
    const close = () => { if (dialog.open) dialog.close(); };
    dialog.addEventListener('cancel', event => { if (!canDismiss()) event.preventDefault(); });
    dialog.addEventListener('click', event => {
      if (!canDismiss()) return;
      if (event.target.closest('[data-sheet-close]')) return close();
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close();
    });
    dialog.addEventListener('close', () => {
      openSheets.delete(dialog);
      if (openSheets.size) return;
      document.body.style.overflow = previousOverflow;
      if (opener?.isConnected && (!opener.closest('dialog') || opener.closest('dialog').open)) opener.focus();
      else if (!document.querySelector('dialog[open]')) document.querySelector('main')?.focus();
    });
    return {
      open() {
        if (dialog.open) return;
        opener = document.activeElement;
        if (!openSheets.size) previousOverflow = document.body.style.overflow;
        openSheets.add(dialog);
        dialog.showModal();
        document.body.style.overflow = 'hidden';
      },
      close,
    };
  },
};

})();
