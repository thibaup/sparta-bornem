(function () {
    const DATA_URL = '/html/images/images-data.json';
    const BATCH_SIZE = 12;
    const folderStates = new Map();
    let lightbox = null;
    let lightboxImage = null;
    let lightboxClose = null;

    const imageObserver = 'IntersectionObserver' in window
        ? new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                const img = entry.target;
                observer.unobserve(img);
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    delete img.dataset.src;
                }
            });
        }, { rootMargin: '350px 0px' })
        : null;

    const loadObserver = 'IntersectionObserver' in window
        ? new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                const folderId = entry.target.dataset.folderId;
                const state = folderStates.get(folderId);
                if (!state || state.isRenderingBatch) return;

                state.isRenderingBatch = true;
                loadObserver.unobserve(state.sentinel);
                renderNextBatch(state);

                requestAnimationFrame(() => {
                    state.isRenderingBatch = false;
                    updateLoadControls(state);
                });
            });
        }, { rootMargin: '600px 0px' })
        : null;

    function normalizeText(value, fallback = '') {
        const text = String(value || '').trim();
        return text || fallback;
    }

    function normalizeImageSrc(value) {
        const src = String(value || '').trim();
        if (!src || src.startsWith('data:')) return '';
        try {
            const url = new URL(src, window.location.origin);
            if (url.origin !== window.location.origin) return '';
            return url.pathname + url.search;
        } catch (_error) {
            return '';
        }
    }

    function makeSafeId(value, fallback) {
        const raw = normalizeText(value, fallback)
            .toLowerCase()
            .replace(/[^a-z0-9_-]+/g, '-')
            .replace(/^-+|-+$/g, '');
        return raw || fallback;
    }

    function requestFooterAdjust() {
        if (typeof adjustFooterPosition === 'function') {
            setTimeout(adjustFooterPosition, 80);
        }
    }

    function setStateMessage(element, message, isError) {
        element.textContent = message;
        element.hidden = false;
        element.style.color = isError ? '#9b1c1c' : '';
    }

    function setupLightbox() {
        const box = document.getElementById('images-lightbox');
        const image = document.getElementById('images-lightbox-image');
        const close = document.getElementById('images-lightbox-close');

        if (!box || !image || !close) {
            lightbox = null;
            lightboxImage = null;
            lightboxClose = null;
            return;
        }

        lightbox = box;
        lightboxImage = image;
        lightboxClose = close;

        lightboxClose.addEventListener('click', closeLightbox);
        lightbox.addEventListener('click', event => {
            if (event.target === lightbox) closeLightbox();
        });
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape' && lightbox.classList.contains('active')) {
                closeLightbox();
            }
        });
    }

    function openLightbox(src, alt) {
        if (!lightbox || !lightboxImage || !src) return;
        lightboxImage.src = src;
        lightboxImage.alt = alt || 'Afbeelding';
        lightbox.classList.add('active');
        lightbox.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        setTimeout(() => {
            if (lightboxClose) lightboxClose.focus({ preventScroll: true });
        }, 80);
    }

    function closeLightbox() {
        if (!lightbox || !lightboxImage) return;
        lightbox.classList.remove('active');
        lightbox.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        setTimeout(() => {
            if (!lightbox.classList.contains('active')) {
                lightboxImage.src = '';
                lightboxImage.alt = '';
            }
        }, 250);
    }

    function createFolder(folder, index) {
        const folderData = folder && typeof folder === 'object' ? folder : {};
        const title = normalizeText(folderData.title, 'Naamloze map');
        const images = Array.isArray(folderData.images) ? folderData.images : [];
        const folderId = `${makeSafeId(folderData.id, `folder-${index}`)}-${index}`;

        const article = document.createElement('article');
        article.className = 'images-folder';

        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'images-folder-toggle';
        button.setAttribute('aria-expanded', 'false');
        button.setAttribute('aria-controls', `images-folder-panel-${folderId}`);

        const titleWrap = document.createElement('span');
        titleWrap.className = 'images-folder-title';

        const icon = document.createElement('span');
        icon.className = 'images-folder-icon';
        icon.setAttribute('aria-hidden', 'true');

        const name = document.createElement('span');
        name.className = 'images-folder-name';
        name.textContent = title;

        titleWrap.append(icon, name);

        const meta = document.createElement('span');
        meta.className = 'images-folder-meta';
        const count = document.createElement('span');
        count.textContent = `${images.length} afbeelding${images.length === 1 ? '' : 'en'}`;
        const chevron = document.createElement('span');
        chevron.className = 'images-folder-chevron';
        chevron.setAttribute('aria-hidden', 'true');
        meta.append(count, chevron);

        button.append(titleWrap, meta);

        const panel = document.createElement('div');
        panel.className = 'images-folder-panel';
        panel.id = `images-folder-panel-${folderId}`;
        panel.hidden = true;

        const gallery = document.createElement('div');
        gallery.className = 'images-gallery';

        const empty = document.createElement('div');
        empty.className = 'images-empty-folder';
        empty.textContent = 'Deze map bevat nog geen afbeeldingen.';
        empty.hidden = images.length > 0;

        const sentinel = document.createElement('div');
        sentinel.className = 'images-sentinel';
        sentinel.dataset.folderId = folderId;

        const loadMore = document.createElement('button');
        loadMore.type = 'button';
        loadMore.className = 'images-load-more';
        loadMore.textContent = 'Meer laden';
        loadMore.hidden = true;

        panel.append(empty, gallery, sentinel, loadMore);
        article.append(button, panel);

        const state = {
            folderId,
            folder: folderData,
            images,
            gallery,
            sentinel,
            loadMore,
            rendered: 0,
            initialized: false,
            isRenderingBatch: false
        };
        folderStates.set(folderId, state);

        button.addEventListener('click', () => {
            const willOpen = !article.classList.contains('is-open');
            article.classList.toggle('is-open', willOpen);
            button.setAttribute('aria-expanded', String(willOpen));
            panel.hidden = !willOpen;
            if (willOpen && !state.initialized) {
                state.initialized = true;
                renderNextBatch(state);
            }
            requestFooterAdjust();
        });

        loadMore.addEventListener('click', () => renderNextBatch(state));

        return article;
    }

    function createImageCard(imageData, index) {
        const image = imageData && typeof imageData === 'object' ? imageData : {};
        const src = normalizeImageSrc(image.src);
        const filename = normalizeText(image.filename, src.split('/').pop() || `Afbeelding ${index + 1}`);
        const alt = normalizeText(image.alt, filename);

        const figure = document.createElement('figure');
        figure.className = 'images-card';

        const frame = document.createElement('div');
        frame.className = 'images-card-frame';

        if (!src) {
            frame.classList.add('images-card-broken');
            frame.textContent = 'Afbeelding niet beschikbaar';
        } else {
            const img = document.createElement('img');
            img.alt = alt;
            img.loading = 'lazy';
            img.decoding = 'async';
            img.dataset.src = src;

            img.addEventListener('load', () => {
                figure.classList.add('is-loaded');
            });
            img.addEventListener('error', () => {
                figure.classList.add('is-broken');
                frame.classList.add('images-card-broken');
                img.remove();
                frame.textContent = 'Afbeelding niet beschikbaar';
                requestFooterAdjust();
            });
            img.addEventListener('click', () => {
                openLightbox(img.currentSrc || img.src || img.dataset.src, img.alt);
            });

            frame.appendChild(img);
            if (imageObserver) {
                imageObserver.observe(img);
            } else {
                img.src = src;
                delete img.dataset.src;
            }
        }

        const caption = document.createElement('figcaption');
        caption.className = 'images-card-caption';
        caption.textContent = filename;
        caption.title = filename;

        figure.append(frame, caption);
        return figure;
    }

    function renderNextBatch(state) {
        if (!state || state.rendered >= state.images.length) {
            updateLoadControls(state);
            return;
        }

        const nextLimit = Math.min(state.rendered + BATCH_SIZE, state.images.length);
        const fragment = document.createDocumentFragment();
        for (let index = state.rendered; index < nextLimit; index += 1) {
            fragment.appendChild(createImageCard(state.images[index], index));
        }
        state.gallery.appendChild(fragment);
        state.rendered = nextLimit;
        updateLoadControls(state);
        requestFooterAdjust();
    }

    function updateLoadControls(state) {
        if (!state) return;
        const hasMore = state.rendered < state.images.length;
        const showButton = hasMore && !loadObserver;

        state.loadMore.hidden = !showButton;
        state.loadMore.classList.toggle('is-visible', showButton);

        if (loadObserver) {
            if (hasMore) {
                loadObserver.observe(state.sentinel);
            } else {
                loadObserver.unobserve(state.sentinel);
            }
        }
    }

    function initImagesPage() {
        setupLightbox();
        loadImagesPage();
    }

    async function loadImagesPage() {
        const loading = document.getElementById('images-loading');
        const empty = document.getElementById('images-empty');
        const foldersContainer = document.getElementById('images-folders');
        const heading = document.getElementById('images-heading');
        const pageTitle = document.getElementById('page-title');

        if (!loading || !empty || !foldersContainer) return;

        try {
            const response = await fetch(`${DATA_URL}?t=${Date.now()}`, { cache: 'no-store' });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            const folders = Array.isArray(data.folders) ? data.folders : [];

            if (data.pageTitle && pageTitle) {
                pageTitle.textContent = data.pageTitle;
                document.title = data.pageTitle;
            }
            if (data.heading && heading) {
                heading.textContent = data.heading;
            }

            loading.hidden = true;
            foldersContainer.replaceChildren();
            folderStates.clear();

            if (folders.length === 0) {
                empty.hidden = false;
                requestFooterAdjust();
                return;
            }

            empty.hidden = true;
            const fragment = document.createDocumentFragment();
            folders.forEach((folder, index) => {
                fragment.appendChild(createFolder(folder, index));
            });
            foldersContainer.appendChild(fragment);
            requestFooterAdjust();
        } catch (error) {
            console.error('Kon Images data niet laden:', error);
            setStateMessage(loading, 'Kon Images niet laden.', true);
            requestFooterAdjust();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initImagesPage);
    } else {
        initImagesPage();
    }
}());
