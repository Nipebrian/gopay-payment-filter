// ===== Terminal Animation =====
const terminalLines = [
    { text: '', type: '' },
    { text: '============================================================', type: 'header' },
    { text: '  SISTEM FILTER BUKTI PEMBAYARAN GOPAY', type: 'header' },
    { text: '  Kriteria: GoPay + PB MPKMB DRAMAGA', type: 'header' },
    { text: '============================================================', type: 'header' },
    { text: '', type: '' },
    { text: '[INFO] Scanning folder: ./input_batch_all', type: 'info' },
    { text: '[INFO] Ditemukan 5000+ file (gambar & PDF)', type: 'info' },
    { text: '[INFO] Memuat model OCR...', type: 'info' },
    { text: '[INFO] Model OCR siap!', type: 'info' },
    { text: '', type: '' },
    { text: '[1/5000] Memproses: bukti_001.jpg... ✅ COCOK! [2.3s]', type: 'success' },
    { text: '[2/5000] Memproses: bukti_002.pdf... ✅ COCOK! [3.1s]', type: 'success' },
    { text: '[3/5000] Memproses: bukti_003.jpg... ❌ Tidak cocok [1.8s]', type: 'error' },
    { text: '[4/5000] Memproses: bukti_004.png... ✅ COCOK! [2.1s]', type: 'success' },
    { text: '[5/5000] Memproses: bukti_005.jpg... ⚠️  Hanya GoPay [1.9s]', type: 'warn' },
    { text: '[6/5000] Memproses: bukti_006.pdf... ✅ COCOK! [2.8s]', type: 'success' },
    { text: '[7/5000] Memproses: bukti_007.jpg... ❌ Tidak cocok [1.7s]', type: 'error' },
    { text: '[8/5000] Memproses: bukti_008.jpg... ✅ COCOK! [2.0s]', type: 'success' },
    { text: '...', type: 'dim' },
    { text: '', type: '' },
    { text: '============================================================', type: 'header' },
    { text: '  HASIL FILTER', type: 'header' },
    { text: '============================================================', type: 'header' },
    { text: '  Total file diproses    : 5000+', type: '' },
    { text: '  ✅ Lolos filter (cocok) : 580', type: 'success' },
    { text: '  ⚠️  Hanya GoPay         : 43', type: 'warn' },
    { text: '  ❌ Tidak cocok          : 4377+', type: 'error' },
    { text: '  🎯 Akurasi             : ~95%', type: 'success' },
    { text: '============================================================', type: 'header' },
    { text: '', type: '' },
    { text: 'Selesai! 🎉', type: 'success' },
];

function runTerminalAnimation() {
    const terminal = document.getElementById('terminal-output');
    if (!terminal) return;

    let lineIndex = 0;
    const interval = setInterval(() => {
        if (lineIndex >= terminalLines.length) {
            clearInterval(interval);
            // Restart after a pause
            setTimeout(() => {
                terminal.innerHTML = '<div class="term-line"><span class="term-prompt">$</span> python filter_pembayaran.py ./input ./output</div>';
                lineIndex = 0;
                runTerminalAnimation();
            }, 5000);
            return;
        }

        const line = terminalLines[lineIndex];
        const div = document.createElement('div');
        div.className = 'term-line';
        if (line.type) div.classList.add('term-' + line.type);
        div.textContent = line.text;
        terminal.appendChild(div);
        terminal.scrollTop = terminal.scrollHeight;
        lineIndex++;
    }, 150);
}

// ===== Stat Counter Animation =====
function animateCounters() {
    const counters = document.querySelectorAll('.stat-number');
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-target'));
        const duration = 2000;
        const start = performance.now();

        function update(now) {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            // Ease out
            const eased = 1 - Math.pow(1 - progress, 3);
            counter.textContent = Math.floor(eased * target);
            if (progress < 1) requestAnimationFrame(update);
            else counter.textContent = target;
        }
        requestAnimationFrame(update);
    });
}

// ===== Navbar Scroll =====
window.addEventListener('scroll', () => {
    const navbar = document.getElementById('navbar');
    if (navbar) {
        navbar.classList.toggle('scrolled', window.scrollY > 50);
    }
});

// ===== Code Tabs =====
document.querySelectorAll('.code-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.code-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.code-panel').forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        const panel = document.getElementById('panel-' + tab.dataset.tab);
        if (panel) panel.classList.add('active');
    });
});

// ===== Copy Code =====
function copyCode(btn) {
    const codeBlock = btn.closest('.code-block');
    const code = codeBlock.querySelector('code').innerText;
    navigator.clipboard.writeText(code).then(() => {
        btn.textContent = '✅ Copied!';
        setTimeout(() => btn.textContent = '📋 Copy', 2000);
    });
}

// ===== Intersection Observer for Animations =====
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            // Trigger counter animation when stats are visible
            if (entry.target.classList.contains('hero-stats')) {
                animateCounters();
            }
        }
    });
}, { threshold: 0.2 });

document.querySelectorAll('.feature-card, .overview-card, .pipeline-step, .tech-card, .hero-stats').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(el);
});

// Add visible class styles
const style = document.createElement('style');
style.textContent = `.visible { opacity: 1 !important; transform: translateY(0) !important; }`;
document.head.appendChild(style);

// ===== Stagger animation delay =====
document.querySelectorAll('.features-grid .feature-card').forEach((card, i) => {
    card.style.transitionDelay = (i * 0.1) + 's';
});
document.querySelectorAll('.tech-grid .tech-card').forEach((card, i) => {
    card.style.transitionDelay = (i * 0.08) + 's';
});
document.querySelectorAll('.pipeline .pipeline-step').forEach((step, i) => {
    step.style.transitionDelay = (i * 0.12) + 's';
});

// ===== Init =====
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(runTerminalAnimation, 1000);
});
