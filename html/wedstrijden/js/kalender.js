document.addEventListener('DOMContentLoaded', function() {
    const jsonPath = '/html/wedstrijden/json/kalender.json';
    const calendarViewContainer = document.getElementById('calendar-view-container');
    const pageTitleElement = document.getElementById('page-title');
    const mainHeadingElement = document.getElementById('main-heading');
    const legendTitleElement = document.getElementById('legend-title');
    const legendItemsContainer = document.getElementById('calendar-legend');

    if (!calendarViewContainer) {
        console.error('Placeholder element #calendar-view-container not found.');
        return;
    }

    const dutchMonths = [
        "Januari", "Februari", "Maart", "April", "Mei", "Juni",
        "Juli", "Augustus", "September", "Oktober", "November", "December"
    ];
    const dayAbbreviations = ["M", "D", "W", "D", "V", "Z", "Z"];

    fetch(jsonPath)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status} while fetching ${jsonPath}`);
            }
            return response.json();
        })
        .then(data => {
            calendarViewContainer.innerHTML = ''; 

            if (data.pageTitle && pageTitleElement) pageTitleElement.textContent = data.pageTitle;
            if (data.mainHeading && mainHeadingElement) mainHeadingElement.textContent = data.mainHeading;

            if (data.legend && legendItemsContainer && legendTitleElement) {
                if(data.legend.title) legendTitleElement.textContent = data.legend.title;
                data.legend.items.forEach(item => {
                    const p = document.createElement('p');
                    const span = document.createElement('span');
                    span.className = item.colorClass;
                    span.textContent = item.label + " ";
                    p.appendChild(span);
                    p.appendChild(document.createTextNode(item.description));
                    legendItemsContainer.appendChild(p);
                });
            }

            if (!data.events || data.events.length === 0) {
            }

            const eventsByDate = (data.events || []).reduce((acc, event) => {
                if (!acc[event.date]) {
                    acc[event.date] = [];
                }
                acc[event.date].push(event);
                return acc;
            }, {});

            let monthsToRender = data.displayedMonths;

            if (!monthsToRender || !Array.isArray(monthsToRender) || monthsToRender.length === 0) {
                console.warn("'displayedMonths' not found or empty in JSON, inferring from all events.");
                const inferredMonthsSet = new Set();
                (data.events || []).forEach(event => {
                    if (event && event.date) {
                        inferredMonthsSet.add(event.date.substring(0, 7));
                    }
                });
                monthsToRender = Array.from(inferredMonthsSet).sort().map(ym => {
                    const [y, m] = ym.split('-').map(Number);
                    return [y, m];
                });
            } else {
                monthsToRender.sort((a, b) => {
                    if (a[0] !== b[0]) return a[0] - b[0];
                    return a[1] - b[1];
                });
            }

            if (monthsToRender.length === 0 && (!data.events || data.events.length === 0) ) {
                calendarViewContainer.innerHTML = '<p>Geen evenementen of maanden voor weergave gevonden.</p>';
                return;
            }


            monthsToRender.forEach(yearMonthArray => {
                if (!Array.isArray(yearMonthArray) || yearMonthArray.length !== 2) {
                    console.warn("Skipping invalid month entry in displayedMonths:", yearMonthArray);
                    return;
                }
                const year = yearMonthArray[0];
                const monthNum = yearMonthArray[1];
                const monthName = dutchMonths[monthNum - 1];

                const monthGridSection = document.createElement('section');
                monthGridSection.className = 'month-grid';

                const h2MonthTitle = document.createElement('h2');
                h2MonthTitle.className = 'month-title';
                h2MonthTitle.textContent = `${monthName} ${year}`;
                monthGridSection.appendChild(h2MonthTitle);

                const calendarHeaderDiv = document.createElement('div');
                calendarHeaderDiv.className = 'calendar-header';
                dayAbbreviations.forEach(abbr => {
                    const spanAbbr = document.createElement('span');
                    spanAbbr.textContent = abbr;
                    calendarHeaderDiv.appendChild(spanAbbr);
                });
                monthGridSection.appendChild(calendarHeaderDiv);

                const calendarDaysDiv = document.createElement('div');
                calendarDaysDiv.className = 'calendar-days';

                const firstDayOfMonth = new Date(year, monthNum - 1, 1);
                let startingDayOfWeek = firstDayOfMonth.getDay(); // 0=Sun, 1=Mon,...
                if (startingDayOfWeek === 0) startingDayOfWeek = 6; // Adjust Sunday to be 6 (last day for 0-6 index)
                else startingDayOfWeek -= 1; // Adjust Mon=0, Tue=1,...

                let totalCellsRendered = 0;

                // Add leading padding days
                for (let i = 0; i < startingDayOfWeek; i++) {
                    const paddingDayDiv = document.createElement('div');
                    paddingDayDiv.className = 'calendar-day padding-day';
                    calendarDaysDiv.appendChild(paddingDayDiv);
                    totalCellsRendered++;
                }

                // Add actual days of the month
                const daysInMonth = new Date(year, monthNum, 0).getDate();
                for (let day = 1; day <= daysInMonth; day++) {
                    const dayDiv = document.createElement('div');
                    dayDiv.className = 'calendar-day';
                    const dayNumberSpan = document.createElement('span');
                    dayNumberSpan.className = 'day-number';
                    dayNumberSpan.textContent = day;
                    dayDiv.appendChild(dayNumberSpan);

                    const currentDateStr = `${year}-${String(monthNum).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                    if (eventsByDate[currentDateStr]) {
                        eventsByDate[currentDateStr].forEach(event => {
                            const eventSpan = document.createElement('span');
                            eventSpan.className = `calendar-event event-${event.color || 'black'}`;
                            eventSpan.title = event.title || event.name;
                            if (event.data_info) eventSpan.dataset.info = event.data_info;
                            if (event.data_location) eventSpan.dataset.location = event.data_location;
                            if (event.data_category) eventSpan.dataset.category = event.data_category;
                            if (event.data_url) eventSpan.dataset.url = event.data_url;
                            
                            if (event.data_url && event.data_url !== '#') {
                                const link = document.createElement('a');
                                link.href = event.data_url;
                                link.textContent = event.name;
                                eventSpan.appendChild(link);
                            } else {
                                eventSpan.textContent = event.name;
                            }
                            dayDiv.appendChild(eventSpan);
                        });
                    }
                    calendarDaysDiv.appendChild(dayDiv);
                    totalCellsRendered++;
                }

                // Add trailing padding days
                // Total cells in a full grid are usually a multiple of 7 (e.g., 35 for 5 weeks, 42 for 6 weeks)
                const cellsInFullGrid = Math.ceil(totalCellsRendered / 7) * 7;
                const trailingPaddingDaysNeeded = cellsInFullGrid - totalCellsRendered;

                for (let i = 0; i < trailingPaddingDaysNeeded; i++) {
                    const paddingDayDiv = document.createElement('div');
                    paddingDayDiv.className = 'calendar-day padding-day';
                    calendarDaysDiv.appendChild(paddingDayDiv);
                }

                monthGridSection.appendChild(calendarDaysDiv);
                calendarViewContainer.appendChild(monthGridSection);
            });
        })
        .catch(error => {
            console.error('Error loading or processing kalender data:', error);
            if (calendarViewContainer) { // Check if container still exists
                 calendarViewContainer.innerHTML = '<p style="color: red;">Kon kalender niet laden.</p>';
            }
        });
});