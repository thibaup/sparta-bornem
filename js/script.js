

let resizeTimerFooter; 

function adjustFooterPosition() {
    const footerElement = document.querySelector('.site-footer');
    const body = document.body;
    const html = document.documentElement;

    if (!footerElement) {
        return;
    }

    setTimeout(() => {
        const totalPageHeight = Math.max( body.scrollHeight, body.offsetHeight,
                               html.clientHeight, html.scrollHeight, html.offsetHeight );
        const viewportHeight = window.innerHeight;

        if (totalPageHeight <= viewportHeight) {

            footerElement.style.position = 'absolute';
            footerElement.style.left = '0';
            footerElement.style.width = '100%';
            footerElement.style.bottom = '0';
        } else {
            footerElement.style.position = ''; 
            footerElement.style.left = '';
            footerElement.style.width = '';
            footerElement.style.bottom = '';
        }
    }, 10);
}


function debounceFooterAdjust() {
    clearTimeout(resizeTimerFooter);
    resizeTimerFooter = setTimeout(adjustFooterPosition, 150);
}

async function loadLatestNews(count = 3, containerId = 'latest-news-grid', loadingId = 'latest-news-loading') {
    const newsContainer = document.getElementById(containerId);
    const loadingMessage = document.getElementById(loadingId);

    if (!newsContainer) {
        return;
    }

    const newsDataUrl = '/html/nieuws/nieuws-data.json';

    try {
        const response = await fetch(newsDataUrl);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status} fetching ${newsDataUrl}`);
        }
        const newsData = await response.json();

        newsData.sort((a, b) => new Date(b.date) - new Date(a.date));

        const latestNews = newsData.slice(0, count);

        if (loadingMessage) loadingMessage.remove();
        newsContainer.innerHTML = '';

        if (latestNews.length === 0) {
            newsContainer.innerHTML = '<p style="grid-column: 1 / -1; text-align: center;">Geen nieuwsberichten gevonden.</p>';
            return; 
        }

        const referrerPath = window.location.pathname;

        latestNews.forEach(item => {
            const itemDate = new Date(item.date);
            const formattedDate = itemDate.toLocaleDateString('nl-BE', {
                day: 'numeric', month: 'long', year: 'numeric'
            });

            let finalImageUrl = '/images/nieuws/placeholder-news.png'; 
            if (item.image) { 
                if (!item.image.startsWith('http://') && !item.image.startsWith('https://')) {
                    finalImageUrl = `/images/nieuws/${item.image.trim()}`;
                } else {
                    finalImageUrl = item.image.trim();
                }
            }

            const summaryText = item.summary || '';
            const itemLink = `/html/nieuws/artikel.html?id=${item.id || ''}&ref=${encodeURIComponent(referrerPath)}`;

            let articleHtml;
            if (summaryText) {
                articleHtml = `
                <article class="news-item" id="latest-${item.id || ''}">
                    <img src="${finalImageUrl}" alt="${item.title}" loading="lazy">
                    <div class="news-content">
                        <h3><a href="${itemLink}">${item.title}</a></h3>
                        <p class="news-meta">${formattedDate} | ${item.category || 'Algemeen'}</p>
                        <p>${summaryText}</p>
                        <a href="${itemLink}" class="read-more">Lees meer »</a>
                    </div>
                </article>
                `;
            } else {
                 articleHtml = `
                 <article class="news-item" id="latest-${item.id || ''}">
                     <img src="${finalImageUrl}" alt="${item.title}" loading="lazy">
                     <div class="news-content">
                         <h3><a href="${itemLink}">${item.title}</a></h3>
                         <p class="news-meta">${formattedDate} | ${item.category || 'Algemeen'}</p>
                         <a href="${itemLink}" class="read-more">Lees meer »</a>
                     </div>
                 </article>
             `;
            }

            newsContainer.insertAdjacentHTML('beforeend', articleHtml);
        });

    } catch (error) {
        console.error('Error loading or processing latest news data:', error);
        const displayError = `<p style="color:red; text-align:center; grid-column: 1 / -1;">Kon laatste nieuws niet laden. (${error.message})</p>`;
        if(loadingMessage) {
            loadingMessage.innerHTML = displayError;
        } else if(newsContainer) {
             newsContainer.innerHTML = displayError;
        }
    }
}


document.addEventListener('DOMContentLoaded', function() {
    const headerPlaceholder = document.getElementById('header-placeholder');
    const footerPlaceholder = document.getElementById('footer-placeholder');

    const currentPagePath = window.location.pathname;


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
        const mainNavUl = document.querySelector('.main-nav > ul');
        const mobileBreakpoint = 992;

        if (menuToggle && mainNavUl) {
            menuToggle.addEventListener('click', () => {
                const isActive = mainNavUl.classList.toggle('active'); 
                menuToggle.innerHTML = isActive ? '✕' : '☰'; 
                menuToggle.setAttribute('aria-expanded', isActive);
                if (isActive && !mainNavUl.dataset.firstOpened) {
                    mainNavUl.dataset.firstOpened = 'true';
                    mainNavUl.classList.add('menu-first-open');
                    mainNavUl.addEventListener('animationend', () => {
                        mainNavUl.classList.remove('menu-first-open');
                    }, { once: true });
                }

                if (!isActive) {
                    mainNavUl.querySelectorAll('li.submenu-open').forEach(li => {
                        li.classList.remove('submenu-open');
                        const sub = li.querySelector(':scope > ul.submenu');
                        if (sub) {
                            sub.classList.remove('submenu-active');
                        }
                        const parentLink = li.querySelector(':scope > a');
                        if (parentLink) {
                            parentLink.setAttribute('aria-expanded', 'false');
                        }
                    });
                }
            });
        } else {
            console.warn("Header initialization warning: Menu toggle button or nav UL not found.");
        }

        const menuItems = mainNavUl.querySelectorAll(':scope > li');

        menuItems.forEach(li => {
            const parentLink = li.querySelector(':scope > a');
            const submenu = li.querySelector(':scope > ul.submenu'); 

            if (parentLink && submenu) {
                 parentLink.setAttribute('aria-haspopup', 'true');
                 parentLink.setAttribute('aria-expanded', 'false');

                parentLink.addEventListener('click', (event) => {
                    const isMobileView = window.innerWidth < mobileBreakpoint && getComputedStyle(menuToggle).display !== 'none';

                    if (isMobileView) {
                        if(parentLink.getAttribute('href') && parentLink.getAttribute('href') !== '#') {
                             event.preventDefault();
                        }

                        const isOpening = !li.classList.contains('submenu-open');

                         if (isOpening) {
                             li.parentElement.querySelectorAll(':scope > li.submenu-open').forEach(otherLi => {
                                 if (otherLi !== li) {
                                     otherLi.classList.remove('submenu-open');
                                     const otherSubmenu = otherLi.querySelector(':scope > ul.submenu');
                                     if (otherSubmenu) otherSubmenu.classList.remove('submenu-active');
                                     const otherLink = otherLi.querySelector(':scope > a');
                                      if(otherLink) {
                                         otherLink.setAttribute('aria-expanded', 'false');
                                      }
                                 }
                             });
                         }

                        
                        li.classList.toggle('submenu-open', isOpening);
                        submenu.classList.toggle('submenu-active', isOpening);
                        parentLink.setAttribute('aria-expanded', isOpening);

                    }
                });

                 const nestedSubmenuItems = submenu.querySelectorAll(':scope > li');
                 nestedSubmenuItems.forEach(nestedLi => {
                     const nestedParentLink = nestedLi.querySelector(':scope > a');
                     const nestedSubmenu = nestedLi.querySelector(':scope > ul.submenu');

                     if (nestedParentLink && nestedSubmenu) {
                         nestedParentLink.setAttribute('aria-haspopup', 'true');
                         nestedParentLink.setAttribute('aria-expanded', 'false');

                         nestedParentLink.addEventListener('click', (event) => {
                             const isMobileView = window.innerWidth < mobileBreakpoint && getComputedStyle(menuToggle).display !== 'none';
                             if (isMobileView) {
                                 if(nestedParentLink.getAttribute('href') && nestedParentLink.getAttribute('href') !== '#') {
                                      event.preventDefault();
                                 }
                                 const isNestedOpening = !nestedLi.classList.contains('submenu-open');

                                 if (isNestedOpening) {
                                    nestedLi.parentElement.querySelectorAll(':scope > li.submenu-open').forEach(otherNestedLi => {
                                        if(otherNestedLi !== nestedLi) {
                                            otherNestedLi.classList.remove('submenu-open');
                                            const otherNestedSub = otherNestedLi.querySelector(':scope > ul.submenu');
                                            if(otherNestedSub) otherNestedSub.classList.remove('submenu-active');
                                            const otherNestedLink = otherNestedLi.querySelector(':scope > a');
                                            if(otherNestedLink) otherNestedLink.setAttribute('aria-expanded', 'false');
                                        }
                                    });
                                 }

                                 nestedLi.classList.toggle('submenu-open', isNestedOpening);
                                 nestedSubmenu.classList.toggle('submenu-active', isNestedOpening);
                                 nestedParentLink.setAttribute('aria-expanded', isNestedOpening);
                             }
                         });
                     }
                 });


            } 
        });

        const navLinks = mainNavUl.querySelectorAll('a[href]'); 

        const normalizePath = (path) => {
            if (!path) return '/'; 

             try {
                path = decodeURIComponent(path);
            } catch (e) {
                 console.warn("Could not decode path component:", path, e);
            }

            if (path.endsWith('/index.html')) {
                path = path.substring(0, path.length - 'index.html'.length);
            } else if (path.endsWith('/home.html')) {
                 path = path.substring(0, path.length - 'home.html'.length);
            }

            if (path.endsWith('.html')) {
                path = path.substring(0, path.length - '.html'.length);
            }

            if (path !== '/' && path.endsWith('/')) {
                path = path.substring(0, path.length - 1);
            }

            if (path === '') {
                path = '/';
            }

            path = path.toLowerCase();

            return path;
        };


        const normalizedCurrentPath = normalizePath(currentPagePath);

        navLinks.forEach(link => {
            const linkHref = link.getAttribute('href');
            if (!linkHref || linkHref === '#') return;

            let linkPath;
            try {
                linkPath = new URL(linkHref, window.location.origin).pathname;
            } catch (e) {
                console.warn(`Invalid URL encountered in navigation: ${linkHref}`);
                return;
            }

            const normalizedLinkPath = normalizePath(linkPath);

            if (normalizedCurrentPath === normalizedLinkPath) {
                link.classList.add('active');

                let currentElement = link.parentElement;
                while (currentElement && currentElement.matches('.main-nav li, .main-nav ul')) {
                    if (currentElement.tagName === 'LI') {
                        currentElement.classList.add('active-ancestor'); 

                        const parentTriggerLink = currentElement.querySelector(':scope > a');
                        if (parentTriggerLink) {
                            parentTriggerLink.classList.add('active');
                        }
                    }
                     const parentUl = currentElement.closest('ul.submenu');
                     if (parentUl) {
                         currentElement = parentUl.parentElement;
                     } else {
                         break; 
                     }
                }
            } 
        });


    }; 

    const initializeFooter = () => {
         const yearSpan = document.getElementById('current-year');
         if (yearSpan) {
             yearSpan.textContent = new Date().getFullYear();
         }
    };


    const loadAll = async () => {
        let headerLoaded = false;
        let footerLoaded = false;

        const headerPath = '/_header.html'; 
        const footerPath = '/_footer.html';

        if (headerPlaceholder) {
            headerLoaded = await loadHTML(headerPath, headerPlaceholder);
        }
        if (document.querySelector('.site-header')) {
             initializeHeader();
        } else {
            console.warn("loadAll: .site-header not found after attempting load/checking static.");
        }

        if (footerPlaceholder) {
             footerLoaded = await loadHTML(footerPath, footerPlaceholder);
        }

         if (document.querySelector('.site-footer')) {
             initializeFooter();
             adjustFooterPosition();
         } else {
             console.warn("loadAll: .site-footer not found after attempting load/checking static.");r
             adjustFooterPosition();
         }


        if (typeof loadLatestNews === 'function') {
           await loadLatestNews(); 
        }


        if (typeof adjustFooterPosition === 'function') {
            setTimeout(adjustFooterPosition, 100);
        }

    }; 

    loadAll();

}); 

window.addEventListener('load', adjustFooterPosition);
window.addEventListener('resize', debounceFooterAdjust);

