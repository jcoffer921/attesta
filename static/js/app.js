(() => {
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const shell = $('[data-shell]');
  const backdrop = $('[data-drawer-close].drawer-backdrop');

  const toast = (message) => {
    const box = $('[data-toast-box]');
    if (!box) return;
    $('span', box).textContent = message;
    box.classList.add('show');
    clearTimeout(window.attestaToastTimer);
    window.attestaToastTimer = setTimeout(() => box.classList.remove('show'), 2600);
  };

  $$('[data-toast]').forEach(el => el.addEventListener('click', event => {
    if (el.tagName === 'A' && el.getAttribute('href') === '#') event.preventDefault();
    toast(el.dataset.toast);
  }));

  $$('[data-sidebar-toggle]').forEach(button => button.addEventListener('click', () => {
    if (window.innerWidth <= 850) $('#sidebar')?.classList.toggle('mobile-open');
    else {
      shell?.classList.toggle('collapsed');
      localStorage.setItem('attesta-sidebar', shell?.classList.contains('collapsed') ? 'collapsed' : 'open');
    }
  }));
  if (shell && localStorage.getItem('attesta-sidebar') === 'collapsed' && window.innerWidth > 850) shell.classList.add('collapsed');

  $('[data-dropdown-toggle]')?.addEventListener('click', () => $('[data-dropdown]')?.classList.toggle('open'));
  document.addEventListener('click', event => {
    if (!event.target.closest('[data-dropdown-toggle], [data-dropdown]')) $('[data-dropdown]')?.classList.remove('open');
  });

  const closeDrawers = () => {
    $$('.detail-drawer.open, [data-builder].open').forEach(el => el.classList.remove('open'));
    backdrop?.classList.remove('open');
    $('#sidebar')?.classList.remove('mobile-open');
  };
  $$('[data-detail]').forEach(row => {
    const open = event => {
      if (event.target.matches('input,button,a')) return;
      const drawer = document.getElementById(row.dataset.detail);
      drawer?.classList.add('open');
      backdrop?.classList.add('open');
    };
    row.addEventListener('click', open);
    row.addEventListener('keydown', event => { if (event.key === 'Enter') open(event); });
  });
  $$('[data-drawer-close]').forEach(el => el.addEventListener('click', closeDrawers));

  $$('[data-modal-open]').forEach(button => button.addEventListener('click', () => document.getElementById(button.dataset.modalOpen)?.classList.add('open')));
  $$('[data-modal-close]').forEach(button => button.addEventListener('click', () => button.closest('.modal')?.classList.remove('open')));

  $$('[data-builder-open]').forEach(button => button.addEventListener('click', () => {
    $('[data-builder]')?.classList.add('open');
    backdrop?.classList.add('open');
  }));
  $$('[data-builder-close]').forEach(button => button.addEventListener('click', closeDrawers));
  $('[data-generate-report]')?.addEventListener('click', event => {
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = 'Generating…';
    setTimeout(() => { closeDrawers(); button.disabled = false; button.textContent = 'Generate Report'; toast('Report generated and ready to download'); }, 1200);
  });

  const fileInput = $('[data-file-input]');
  $$('[data-upload-trigger]').forEach(button => button.addEventListener('click', () => fileInput?.click()));
  fileInput?.addEventListener('change', () => fileInput.files.length && toast(`${fileInput.files.length} file${fileInput.files.length > 1 ? 's' : ''} queued for upload`));
  const zone = $('[data-upload-zone]');
  ['dragenter', 'dragover'].forEach(name => zone?.addEventListener(name, event => { event.preventDefault(); zone.classList.add('dragging'); }));
  ['dragleave', 'drop'].forEach(name => zone?.addEventListener(name, event => { event.preventDefault(); zone.classList.remove('dragging'); if (name === 'drop') toast(`${event.dataTransfer.files.length} file(s) queued for upload`); }));

  $$('[data-table-search]').forEach(input => input.addEventListener('input', () => {
    const table = input.closest('.table-card')?.querySelector('table');
    $$('tbody tr', table).forEach(row => row.hidden = !row.textContent.toLowerCase().includes(input.value.toLowerCase()));
  }));
  $$('[data-filter]').forEach(select => select.addEventListener('change', () => {
    const card = select.closest('.table-card');
    const active = $$('[data-filter]', card).map(item => item.value.toLowerCase()).filter(Boolean);
    $$('tbody tr', card).forEach(row => row.hidden = !active.every(value => row.textContent.toLowerCase().includes(value)));
  }));

  $$('[data-settings-tab]').forEach(tab => tab.addEventListener('click', () => {
    $$('[data-settings-tab]').forEach(el => el.classList.remove('active'));
    $$('.settings-panel').forEach(el => el.classList.remove('active'));
    tab.classList.add('active');
    $(`[data-panel="${tab.dataset.settingsTab}"]`)?.classList.add('active');
  }));
  $$('[data-save-settings]').forEach(button => button.addEventListener('click', () => toast('Settings saved successfully')));

  $('[data-password-toggle]')?.addEventListener('click', event => {
    const input = event.currentTarget.previousElementSibling;
    input.type = input.type === 'password' ? 'text' : 'password';
    event.currentTarget.textContent = input.type === 'password' ? 'Show' : 'Hide';
  });
  $('[data-ai-rerun]')?.addEventListener('click', event => {
    const button = event.currentTarget;
    button.innerHTML = 'Analyzing…'; button.disabled = true;
    setTimeout(() => { button.innerHTML = '<svg><use href="#i-spark"/></svg> Re-run analysis'; button.disabled = false; toast('AI analysis updated — human verification required'); }, 1300);
  });

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') { closeDrawers(); $$('.modal.open').forEach(el => el.classList.remove('open')); }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); $('.global-search input')?.focus(); }
  });
})();
