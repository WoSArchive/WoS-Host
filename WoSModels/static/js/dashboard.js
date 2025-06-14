// Dashboard JavaScript Functions

// Modal Functions
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// Upload Mode Toggle
function toggleUploadMode(suffix) {
  const zipRadio = document.getElementById(`zip_radio_${suffix}`);
  const zipInput = document.getElementById(`zip_input_${suffix}`);
  const urlInput = document.getElementById(`url_input_${suffix}`);

  if (zipRadio && zipInput && urlInput) {
    const isZip = zipRadio.checked;
    zipInput.classList.toggle('hidden', !isZip);
    urlInput.classList.toggle('hidden', isZip);
  }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
  // Enhanced keyboard navigation
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal.active').forEach(m => {
        m.classList.remove('active');
        document.body.style.overflow = '';
      });
    }
  });

  // Enhanced modal backdrop click
  document.addEventListener('click', function (e) {
    if (e.target.classList.contains('modal')) {
      e.target.classList.remove('active');
      document.body.style.overflow = '';
    }
  });

  // Smooth animations for buttons
  document.querySelectorAll('.button').forEach(button => {
    button.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-2px)';
    });
    
    button.addEventListener('mouseleave', function() {
      this.style.transform = 'translateY(0)';
    });
  });

  // Auto-focus first input in modals
  document.addEventListener('click', function(e) {
    if (e.target.matches('[onclick*="openModal"]')) {
      setTimeout(() => {
        const activeModal = document.querySelector('.modal.active');
        if (activeModal) {
          const firstInput = activeModal.querySelector('input[type="text"]');
          if (firstInput) firstInput.focus();
        }
      }, 100);
    }
  });
});