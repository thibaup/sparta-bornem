// js/scripts.js

// --- Global Scope Variables and Functions for Footer Positioning ---
let resizeTimerFooter; // Timer variable for debouncing resize

/**
 * Checks page height vs viewport height and sets footer position accordingly.
 * Switches between CSS default (relative) and absolute positioning.
 * Assumes CSS sets body { position: relative; min-height: 100vh; }
 * and .site-footer { position: relative; width: 100%; } as default.
 */
function adjustFooterPosition() {
    const footerElement = document.querySelector('.site-footer'); // Target the actual footer
    const body = document.body;
    const html = document.documentElement;

    if (!footerElement) {
        // console.warn("adjustFooterPosition: Footer element (.site-footer) not found.");
        return; // Exit if footer isn't in the DOM yet
    }

    // Adding a small delay can sometimes help ensure layout calculations are complete
    setTimeout(() => {
        const totalPageHeight = Math.max( body.scrollHeight, body.offsetHeight,
                               html.clientHeight, html.scrollHeight, html.offsetHeight );
        const viewportHeight = window.innerHeight;

        // console.log(`DEBUG: Page Height: ${totalPageHeight}, Viewport Height: ${viewportHeight}`);

        if (totalPageHeight <= viewportHeight) {
            // Page content is short: Stick footer absolutely
            // console.log("DEBUG: Setting footer to absolute");
            footerElement.style.position = 'absolute';
            footerElement.style.left = '0';
            footerElement.style.width = '100%';
            footerElement.style.bottom = '0';
        } else {
            // Page content is long: Revert footer to CSS default (relative)
            // console.log("DEBUG: Reverting footer to CSS default position");
            footerElement.style.position = ''; // Let CSS handle 'relative'
            footerElement.style.left = '';
            footerElement.style.width = '';
            footerElement.style.bottom = '';
        }
    }, 10); // Small delay (10ms) - adjust if necessary

}

/**
 * Debounce function to limit how often adjustFooterPosition runs on resize.
 */
function debounceFooterAdjust() {
    clearTimeout(resizeTimerFooter);
    resizeTimerFooter = setTimeout(adjustFooterPosition, 150); // 150ms delay
}

/**
 * Fetches news data, sorts it, takes the latest items, and displays them.
 * Constructs image URLs relative to /images/ if not a full URL.
 * Includes referrer URL in the article link.
 * @param {number} [count=3] - The number of latest news items to display.
 * @param {string} [containerId='latest-news-grid'] - The ID of the container element for the news grid.
 * @param {string} [loadingId='latest-news-loading'] - The ID of the loading message element.
 */
async function loadLatestNews(count = 3, containerId = 'latest-news-grid', loadingId = 'latest-news-loading') {
    const newsContainer = document.getElementById(containerId);
    const loadingMessage = document.getElementById(loadingId);

    // Exit if the target container element doesn't exist on the current page
    if (!newsContainer) {
        // console.log(`DEBUG: News container #${containerId} not found. Skipping latest news load.`);
        return;
    }

    // *** IMPORTANT: Ensure this path correctly points to your JSON file ***
    const newsDataUrl = '/html/nieuws/nieuws-data.json'; // Assuming JSON is in /nieuws/ folder at root

    try {
        // Fetch the news data
        const response = await fetch(newsDataUrl);
        if (!response.ok) {
            // Throw an error if the fetch fails (e.g., 404 Not Found)
            throw new Error(`HTTP error! status: ${response.status} fetching ${newsDataUrl}`);
        }
        const newsData = await response.json(); // Parse the JSON data

        // Sort data by date descending (newest first) using Date objects
        newsData.sort((a, b) => new Date(b.date) - new Date(a.date));

        // Get the specified number of latest news items
        const latestNews = newsData.slice(0, count);

        // Remove the loading message and clear any previous content
        if (loadingMessage) loadingMessage.remove();
        newsContainer.innerHTML = '';

        // Handle case where no news items are found after fetching/sorting
        if (latestNews.length === 0) {
            newsContainer.innerHTML = '<p style="grid-column: 1 / -1; text-align: center;">Geen nieuwsberichten gevonden.</p>';
            return; // Stop execution for this function
        }

        // Get the current page path to pass as a referrer
        const referrerPath = window.location.pathname;

        // Loop through the latest news items and generate HTML for each
        latestNews.forEach(item => {
            // Format the date for display
            const itemDate = new Date(item.date);
            const formattedDate = itemDate.toLocaleDateString('nl-BE', {
                day: 'numeric', month: 'long', year: 'numeric'
            });

            let finalImageUrl = '/images/placeholder-news.png'; 
            if (item.image) { 
                if (!item.image.startsWith('http://') && !item.image.startsWith('https://')) {
                    finalImageUrl = `/images/${item.image}`; 
                } else {
                    finalImageUrl = item.image; 
                }
            }
            const summaryText = item.summary;
            const itemLink = `/html/nieuws/artikel.html?id=${item.id || ''}&ref=${encodeURIComponent(referrerPath)}`;

            let articleHtml
            if (summaryText) {
                articleHtml = `
                <article class="news-item" id="latest-${item.id || ''}">
                    <img src="${finalImageUrl}" alt="${item.title}"
                    <div class="news-content">
                        <p class="news-meta">${formattedDate} | ${item.category || 'Algemeen'}</p>
                        <h3><a href="${itemLink}">${item.title}</a></h3>
                        <p>${summaryText}</p>
                        <a href="${itemLink}" class="read-more">Lees meer »</a>
                    </div>
                </article>
                `;
            } else {
                articleHtml = `
                <article class="news-item" id="latest-${item.id || ''}">
                    <img src="${finalImageUrl}" alt="${item.title}"
                    <div class="news-content">
                        <p class="news-meta">${formattedDate} | ${item.category || 'Algemeen'}</p>
                        <h3><a href="${itemLink}">${item.title}</a></h3>
                    </div>
                </article>
            `;
            }

            newsContainer.insertAdjacentHTML('beforeend', articleHtml);
        });

    } catch (error) {
        // Handle errors during fetch or processing
        console.error('Error loading or processing latest news data:', error);
        const displayError = `<p style="color:red; text-align:center; grid-column: 1 / -1;">Kon laatste nieuws niet laden. (${error.message})</p>`;
        if(loadingMessage) {
            loadingMessage.innerHTML = displayError;
        } else if(newsContainer) {
             newsContainer.innerHTML = displayError;
        }
    }
}

// --- Main Script Logic (Runs after initial HTML is parsed) ---
document.addEventListener('DOMContentLoaded', function() {

    // --- Element Selectors ---
    const headerPlaceholder = document.getElementById('header-placeholder');
    const footerPlaceholder = document.getElementById('footer-placeholder');

    // --- Page Info ---
    // *** IMPORTANT: Adjust 'home.html' if your homepage is index.html or other ***
    const currentPagePath = window.location.pathname; // Get the full path
    let currentPageFilename = currentPagePath.split('/').pop() || 'home.html'; // Default to home.html
    // Handle root case where pop() might be empty
    if (currentPagePath === '/' || currentPagePath.endsWith('/index.html')) {
        currentPageFilename = 'home.html'; // Treat root or index.html as home.html
    }


    // --- Function Definitions within DOMContentLoaded Scope ---

    /**
     * Loads HTML content from a URL into a placeholder element using root-relative paths.
     */
    const loadHTML = async (url, placeholder) => {
        const rootRelativeUrl = url.startsWith('/') ? url : '/' + url;

        try {
            const response = await fetch(rootRelativeUrl);
            if (!response.ok) {
                console.error(`HTTP error! status: ${response.status} for ${rootRelativeUrl}`);
                placeholder.innerHTML = `<p style="color: red; text-align: center;">Error: Could not load ${url}. Check path.</p>`;
                return false;
            }
            const html = await response.text();
            placeholder.innerHTML = html;
            return true;
        } catch (error) {
            console.error(`Could not load HTML from ${rootRelativeUrl}:`, error);
            placeholder.innerHTML = `<p style="color: red; text-align: center;">Error loading content from ${url}.</p>`;
            return false;
        }
    };

    const initializeHeader = () => {
        const menuToggle = document.querySelector('.menu-toggle');
        const mainNavUl = document.querySelector('.main-nav ul');

        if (menuToggle && mainNavUl) {
            menuToggle.addEventListener('click', () => {
                mainNavUl.classList.toggle('active');
                menuToggle.innerHTML = mainNavUl.classList.contains('active') ? '✕' : '☰';
                menuToggle.setAttribute('aria-expanded', mainNavUl.classList.contains('active'));
            });
        } else {
            console.warn("Header initialization warning: Menu toggle button or nav UL not found.");
        }

        const navLinks = document.querySelectorAll('.main-nav a[href]');
        navLinks.forEach(link => {
            const linkHref = link.getAttribute('href');
            if (!linkHref || linkHref === '#') return;

            const linkPath = new URL(linkHref, window.location.origin).pathname;

            const normalizePath = (path) => {
                if (path.endsWith('/index.html')) {
                    path = path.substring(0, path.length - 'index.html'.length);
                }
                if (path !== '/' && path.endsWith('/')) {
                    path = path.substring(0, path.length - 1);
                }

                 if (path === '/home.html') {
                    path = '/';
                 }
                return path;
            };

            const normalizedLinkPath = normalizePath(linkPath);
            const normalizedCurrentPath = normalizePath(currentPagePath);

             let isActive = normalizedCurrentPath === normalizedLinkPath;

             if (normalizedCurrentPath === '/' && normalizedLinkPath === '/') {
                isActive = true;
             }


            if (isActive) {
                link.classList.add('active');
                let currentElement = link;
                while (true) {
                    const parentSubmenu = currentElement.closest('ul.submenu');
                    if (!parentSubmenu) break;
                    const parentLi = parentSubmenu.parentElement;
                    if (parentLi && parentLi.matches('.main-nav li')) {
                        const parentLink = parentLi.querySelector(':scope > a'); // Get parent link (clickable or not)
                        if (parentLink) {
                            parentLink.classList.add('active');
                            currentElement = parentLi;
                        } else { break; }
                    } else { break; }
                }
            }
        });
    };

    const initializeFooter = () => {
         const yearSpan = document.getElementById('current-year');
         if (yearSpan) {
             yearSpan.textContent = new Date().getFullYear();
         } else {
             // console.warn("Footer initialization warning: Element with ID 'current-year' not found.");
         }
    };


    /**
     * Orchestrates the loading and initialization of header and footer,
     * applies local storage content, loads news, and checks footer position.
     */
    const loadAll = async () => {
        let headerLoaded = false;
        let footerLoaded = false;

        const headerPath = '_header.html';
        const footerPath = '_footer.html';

        // --- Load Header ---
        if (headerPlaceholder) {
            headerLoaded = await loadHTML(headerPath, headerPlaceholder);
        }
        // Initialize header AFTER potential loading OR if it exists statically
        if(document.querySelector('.site-header')) {
            initializeHeader();
        } else if (headerLoaded) {
            // Need to ensure initHeader runs *after* innerHTML is processed if loaded
            // Using a microtask delay might help, but direct call is usually ok
             setTimeout(initializeHeader, 0); // Try initializing after a microtask delay
        }


        // --- Load Footer ---
        if (footerPlaceholder) {
             footerLoaded = await loadHTML(footerPath, footerPlaceholder);
        }
         // Initialize footer AFTER potential loading OR if it exists statically
         if (document.querySelector('.site-footer')) {
             initializeFooter();
             adjustFooterPosition(); // Adjust position after footer content is known
         } else if (footerLoaded) {
             setTimeout(() => { // Use delay ensure element exists
                initializeFooter();
                adjustFooterPosition();
            }, 0);
         }

        // --- Load Latest News ---
        // This assumes loadLatestNews is defined globally now
        if (typeof loadLatestNews === 'function') {
           await loadLatestNews(); // Load news if container exists
        }
        // --- Final Footer Position Check ---
        // Call again after potential content changes from localStorage and news load
        if (typeof adjustFooterPosition === 'function') {
            setTimeout(adjustFooterPosition, 100); // Slightly longer delay
        }

    }; // End loadAll

    // --- Start Execution ---
    loadAll();

}); // End DOMContentLoaded


// --- Global Event Listeners ---

// Adjust footer position when all resources are loaded (images etc.)
// This is a good final check for layout shifts
window.addEventListener('load', adjustFooterPosition);

// Adjust footer position on window resize (debounced)
window.addEventListener('resize', debounceFooterAdjust);