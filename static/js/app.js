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
  $$('[data-modal-close]').forEach(button => button.addEventListener('click', () => {
    const modal = button.closest('.modal');
    modal?.classList.remove('open');
    if (modal?.classList.contains('upload-confirmation')) window.history.replaceState({}, '', window.location.pathname);
  }));

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
  const uploadForm = $('[data-upload-form]');
  const uploadModal = $('[data-upload-progress-modal]');
  let uploadRequest = null;

  const formatBytes = bytes => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };
  const uploadElement = selector => uploadModal?.querySelector(selector);
  const setUploadProgress = value => {
    const percent = Math.max(0, Math.min(100, Math.round(value)));
    uploadElement('[data-upload-progress]')?.setAttribute('aria-valuenow', String(percent));
    const bar = uploadElement('[data-upload-progress-bar]');
    if (bar) bar.style.width = `${percent}%`;
    const label = uploadElement('[data-upload-percent]');
    if (label) label.textContent = `${percent}%`;
  };
  const closeUploadModal = () => uploadModal?.classList.remove('open');

  uploadForm?.addEventListener('submit', event => {
    event.preventDefault();
    if (!fileInput?.files.length || uploadRequest) return;

    uploadModal?.classList.add('open');
    uploadModal?.classList.remove('upload-failed', 'upload-succeeded');
    uploadElement('[data-upload-actions]')?.setAttribute('hidden', '');
    uploadElement('[data-upload-stage]').textContent = 'Secure upload';
    uploadElement('[data-upload-title]').textContent = 'Uploading evidence';
    uploadElement('[data-upload-message]').textContent = 'Your document is being transferred to Attesta.';
    uploadElement('[data-upload-detail]').textContent = 'Connecting…';
    setUploadProgress(0);

    const fileList = uploadElement('[data-upload-files]');
    fileList.replaceChildren(...Array.from(fileInput.files, file => {
      const row = document.createElement('div');
      const name = document.createElement('strong');
      const size = document.createElement('span');
      name.textContent = file.name;
      size.textContent = formatBytes(file.size);
      row.append(name, size);
      return row;
    }));

    const request = new XMLHttpRequest();
    uploadRequest = request;
    request.open('POST', uploadForm.action || window.location.href);
    request.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    request.upload.addEventListener('progress', progressEvent => {
      if (!progressEvent.lengthComputable) return;
      const percent = (progressEvent.loaded / progressEvent.total) * 90;
      setUploadProgress(percent);
      uploadElement('[data-upload-detail]').textContent = `Transferred ${formatBytes(progressEvent.loaded)} of ${formatBytes(progressEvent.total)}`;
    });
    request.upload.addEventListener('load', () => {
      setUploadProgress(92);
      uploadElement('[data-upload-stage]').textContent = 'Processing';
      uploadElement('[data-upload-title]').textContent = 'Saving to Evidence';
      uploadElement('[data-upload-message]').textContent = 'Transfer complete. Attesta is validating and saving the document.';
      uploadElement('[data-upload-detail]').textContent = 'Finalizing the Evidence record…';
    });
    request.addEventListener('load', () => {
      uploadRequest = null;
      let payload = {};
      try { payload = JSON.parse(request.responseText); } catch (error) { payload = {}; }
      if (request.status < 200 || request.status >= 300) {
        uploadModal?.classList.add('upload-failed');
        uploadElement('[data-upload-stage]').textContent = 'Upload failed';
        uploadElement('[data-upload-title]').textContent = 'Document was not imported';
        uploadElement('[data-upload-message]').textContent = payload.error || 'Attesta could not save this document. Please try again.';
        uploadElement('[data-upload-detail]').textContent = 'No Evidence record was created.';
        return;
      }

      setUploadProgress(100);
      uploadModal?.classList.add('upload-succeeded');
      uploadElement('[data-upload-stage]').textContent = 'Upload complete';
      uploadElement('[data-upload-title]').textContent = 'Confirm this document';
      uploadElement('[data-upload-message]').textContent = 'The document is saved in Evidence. Confirm it to continue to AI Review.';
      uploadElement('[data-upload-detail]').textContent = payload.message;
      const reviewLink = uploadElement('[data-upload-review]');
      if (reviewLink) reviewLink.href = payload.review_url;
      uploadElement('[data-upload-actions]')?.removeAttribute('hidden');
      $('[data-evidence-empty]')?.remove();
      $('[data-evidence-body]')?.insertAdjacentHTML('afterbegin', payload.rows_html);
      uploadForm.reset();
    });
    request.addEventListener('error', () => {
      uploadRequest = null;
      uploadModal?.classList.add('upload-failed');
      uploadElement('[data-upload-stage]').textContent = 'Connection lost';
      uploadElement('[data-upload-title]').textContent = 'Upload interrupted';
      uploadElement('[data-upload-message]').textContent = 'Check your connection and try the upload again.';
      uploadElement('[data-upload-detail]').textContent = 'The server did not receive the complete document.';
    });
    request.addEventListener('abort', () => { uploadRequest = null; closeUploadModal(); });
    request.send(new FormData(uploadForm));
  });

  uploadElement('[data-upload-cancel]')?.addEventListener('click', () => uploadRequest ? uploadRequest.abort() : closeUploadModal());
  uploadElement('[data-upload-close]')?.addEventListener('click', closeUploadModal);
  $$('[data-upload-trigger]').forEach(button => button.addEventListener('click', () => fileInput?.click()));
  fileInput?.addEventListener('change', () => {
    if (!fileInput.files.length) return;
    toast(`Uploading ${fileInput.files.length} file${fileInput.files.length > 1 ? 's' : ''}…`);
    fileInput.closest('[data-upload-form]')?.requestSubmit();
  });
  const zone = $('[data-upload-zone]');
  ['dragenter', 'dragover'].forEach(name => zone?.addEventListener(name, event => { event.preventDefault(); zone.classList.add('dragging'); }));
  zone?.addEventListener('dragleave', event => { event.preventDefault(); zone.classList.remove('dragging'); });
  zone?.addEventListener('drop', event => {
    event.preventDefault();
    zone.classList.remove('dragging');
    if (!event.dataTransfer.files.length || !fileInput) return;
    fileInput.files = event.dataTransfer.files;
    fileInput.dispatchEvent(new Event('change', { bubbles: true }));
  });
  zone?.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); fileInput?.click(); }
  });

  const reviewForm = $('[data-review-start-form]');
  const reviewPanel = $('[data-review-live]');
  const reviewError = $('[data-review-error]');
  const reviewButton = $('[data-review-submit]');
  const reviewStopButton = $('[data-review-stop]');
  let reviewPollTimer = null;
  let reviewPollRequest = null;
  let reviewActionRequest = null;
  const updateReviewStatus = payload => {
    if (!reviewPanel) return;
    reviewPanel.dataset.reviewStatus = payload.status;
    if (payload.status_url) reviewPanel.dataset.statusUrl = payload.status_url;
    if (reviewStopButton) reviewStopButton.hidden = payload.status !== 'in_review';
    reviewPanel.hidden = payload.status !== 'in_review';
    const step = Number.isInteger(payload.step) ? payload.step : 0;
    reviewPanel.querySelectorAll('[data-step]').forEach(item => {
      const index = Number(item.dataset.step);
      item.classList.toggle('is-done', index < step);
      item.classList.toggle('is-current', index === step);
    });
    document.body.classList.toggle('review-busy', payload.status === 'in_review');
    if (reviewError) {
      reviewError.hidden = payload.status !== 'error';
      if (payload.status === 'error') {
        reviewError.textContent = payload.detail || 'The review could not be completed.';
        reviewError.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
    if (reviewButton) reviewButton.textContent = payload.status === 'stopped' ? 'Resume Review' : payload.status === 'in_review' ? 'Restart Review' : 'Begin Review';
  };
  const pollReviewStatus = () => {
    if (!reviewPanel?.dataset.statusUrl || reviewPanel.dataset.reviewStatus !== 'in_review' || reviewPollRequest) return;
    const request = new XMLHttpRequest();
    reviewPollRequest = request;
    request.open('GET', reviewPanel.dataset.statusUrl);
    request.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    request.addEventListener('load', () => {
      reviewPollRequest = null;
      if (request.status >= 200 && request.status < 300) {
        try {
          const payload = JSON.parse(request.responseText);
          updateReviewStatus(payload);
          // Results are rendered server-side, so reload once the review completes.
          if (payload.status === 'reviewed') { window.location.reload(); return; }
        } catch (error) { /* retry below */ }
      }
      if (reviewPanel.dataset.reviewStatus === 'in_review') reviewPollTimer = window.setTimeout(pollReviewStatus, 3000);
    });
    request.addEventListener('error', () => { reviewPollRequest = null; reviewPollTimer = window.setTimeout(pollReviewStatus, 5000); });
    request.addEventListener('abort', () => { reviewPollRequest = null; });
    request.send();
  };

  reviewForm?.addEventListener('submit', event => {
    if (!reviewPanel) return;
    event.preventDefault();
    const action = event.submitter?.value === 'stop' ? 'stop' : 'start';
    if (reviewActionRequest) return;
    if (reviewPollTimer) window.clearTimeout(reviewPollTimer);
    reviewPollTimer = null;
    reviewPollRequest?.abort();
    reviewButton.disabled = true;
    reviewButton.textContent = 'Starting…';
    updateReviewStatus({ status: 'in_review', stage: 'Starting review', detail: 'Attesta is creating the review workflow…', progress: 10, status_label: 'Starting', step: 0 });

    if (reviewStopButton) reviewStopButton.disabled = true;
    if (action === 'stop') {
      reviewStopButton.textContent = 'Stopping…';
      updateReviewStatus({ status: 'in_review', stage: 'Stopping review', detail: 'Attesta is safely stopping this review…', progress: 35, status_label: 'Stopping', step: 0 });
    }

    const request = new XMLHttpRequest();
    reviewActionRequest = request;
    request.open('POST', reviewForm.action || window.location.href);
    request.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    request.addEventListener('load', () => {
      reviewActionRequest = null;
      let payload = {};
      try { payload = JSON.parse(request.responseText); } catch (error) { payload = {}; }
      reviewButton.disabled = false;
      if (reviewStopButton) { reviewStopButton.disabled = false; reviewStopButton.textContent = 'Stop Review'; }
      if (request.status >= 200 && request.status < 300) {
        updateReviewStatus(payload);
        if (payload.status === 'in_review') pollReviewStatus();
      } else {
        reviewButton.textContent = 'Begin Review';
        updateReviewStatus({ status: 'error', stage: 'Review could not start', detail: payload.error || 'Please try again.', progress: 100, status_label: 'Error' });
      }
    });
    request.addEventListener('error', () => {
      reviewActionRequest = null;
      reviewButton.disabled = false;
      if (reviewStopButton) { reviewStopButton.disabled = false; reviewStopButton.textContent = 'Stop Review'; }
      reviewButton.textContent = 'Begin Review';
      updateReviewStatus({ status: 'error', stage: 'Connection lost', detail: 'The review did not start. Check your connection and try again.', progress: 100, status_label: 'Error' });
    });
    const formData = new FormData(reviewForm);
    formData.set('action', action);
    request.send(formData);
  });

  if (reviewPanel?.dataset.reviewStatus === 'in_review') reviewPollTimer = window.setTimeout(pollReviewStatus, 3000);

  const drawer = $('[data-analysis-drawer]');
  const drawerBackdrop = $('[data-drawer-backdrop]');
  if (drawer) {
    let drawerOpener = null;
    const showTab = name => {
      $$('[data-drawer-tab]', drawer).forEach(tab => tab.setAttribute('aria-selected', String(tab.dataset.drawerTab === name)));
      $$('[data-drawer-panel]', drawer).forEach(panel => { panel.hidden = panel.dataset.drawerPanel !== name; });
      const body = $('.analysis-body', drawer);
      if (body) body.scrollTop = 0;
    };
    const closeDrawer = () => {
      drawer.classList.remove('is-open');
      drawer.hidden = true;
      if (drawerBackdrop) drawerBackdrop.hidden = true;
      document.body.classList.remove('drawer-open');
      drawerOpener?.focus();
    };
    const openDrawer = (tab, opener) => {
      drawerOpener = opener || null;
      showTab(tab || 'overview');
      drawer.hidden = false;
      if (drawerBackdrop) drawerBackdrop.hidden = false;
      document.body.classList.add('drawer-open');
      window.requestAnimationFrame(() => drawer.classList.add('is-open'));
      drawer.focus();
    };
    $$('[data-open-drawer]').forEach(button => button.addEventListener('click', () => openDrawer(button.dataset.openDrawer, button)));
    $$('[data-drawer-tab]', drawer).forEach(tab => tab.addEventListener('click', () => showTab(tab.dataset.drawerTab)));
    $('[data-close-drawer]', drawer)?.addEventListener('click', closeDrawer);
    drawerBackdrop?.addEventListener('click', closeDrawer);
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && !drawer.hidden) closeDrawer(); });
  }

  $('[data-evidence-select]')?.addEventListener('change', event => {
    const evidenceId = event.currentTarget.value;
    window.location.assign(evidenceId ? `${window.location.pathname}?evidence=${encodeURIComponent(evidenceId)}` : window.location.pathname);
  });

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

  $$('[data-password-toggle]').forEach(button => button.addEventListener('click', event => {
    const input = event.currentTarget.parentElement.querySelector('input');
    const showing = input.type === 'password';
    input.type = showing ? 'text' : 'password';
    event.currentTarget.setAttribute('aria-label', showing ? 'Hide password' : 'Show password');
  }));
  $$('[data-auth-form]').forEach(form => form.addEventListener('submit', () => {
    const submit = form.querySelector('[type="submit"]');
    if (!submit) return;
    submit.disabled = true;
    submit.setAttribute('aria-busy', 'true');
    submit.textContent = form.dataset.loadingLabel || 'Please wait…';
  }));
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
