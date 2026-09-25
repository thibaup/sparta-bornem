document.addEventListener('DOMContentLoaded', async () => {
    const list = document.getElementById('faq-list');
    const status = document.getElementById('faq-status');
    if (!list || !status) return;

    try {
        const response = await fetch('faq-data.json', { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const entries = await response.json();
        if (!Array.isArray(entries) || entries.some(item =>
            !item || typeof item.question !== 'string' || !item.question.trim() ||
            typeof item.answer !== 'string' || !item.answer.trim()
        )) {
            throw new Error('Ongeldige FAQ-gegevens');
        }

        if (entries.length === 0) {
            status.textContent = 'Er zijn nog geen vragen toegevoegd.';
            return;
        }

        const fragment = document.createDocumentFragment();
        entries.forEach(({ question, answer }) => {
            const item = document.createElement('details');
            item.className = 'faq-item';

            const summary = document.createElement('summary');
            summary.textContent = question;

            const answerElement = document.createElement('div');
            answerElement.className = 'faq-answer';
            answerElement.textContent = answer;

            item.append(summary, answerElement);
            fragment.appendChild(item);
        });
        list.replaceChildren(fragment);
        status.remove();
    } catch (error) {
        console.error('FAQ laden mislukt:', error);
        status.textContent = 'De veelgestelde vragen konden niet worden geladen. Probeer het later opnieuw.';
    }
});
