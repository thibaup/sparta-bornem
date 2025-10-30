document.addEventListener('DOMContentLoaded', function() {
    const jsonPath = '../info/json/trainers.json';
    const trainingTimesBody = document.getElementById('training-times-body');
    const contactsContainer = document.getElementById('contacts-container');
    const trainerGroupsContainer = document.getElementById('trainer-groups-container');
    const pageTitleElement = document.getElementById('page-title');
    if (!trainingTimesBody || !contactsContainer || !trainerGroupsContainer) {
        console.error('One or more placeholder elements not found in the HTML.');
        return;
    }
    fetch(jsonPath)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status} while fetching ${jsonPath}`);
            return response.json();
        })
        .then(data => {
            if (data.pageTitle && pageTitleElement) {
                pageTitleElement.textContent = data.pageTitle;
            }
            let trainingTimes = [];
            if (Array.isArray(data.times_category_order) && data.trainingTimes) {
                data.times_category_order.forEach(cat => {
                    const item = data.trainingTimes.find(t => t.category === cat);
                    if (item) trainingTimes.push(item);
                });
                data.trainingTimes.forEach(item => {
                    if (!trainingTimes.includes(item)) trainingTimes.push(item);
                });
            } else {
                trainingTimes = data.trainingTimes || [];
            }
            if (trainingTimes.length > 0) {
                trainingTimes.forEach(item => {
                    const row = trainingTimesBody.insertRow();
                    const cellCategory = row.insertCell();
                    cellCategory.innerHTML = item.category;
                    const cellSchedule = row.insertCell();
                    const ul = document.createElement('ul');
                    item.schedule.forEach(s => {
                        const li = document.createElement('li');
                        let scheduleHtml = `<strong>${s.day}:</strong> ${s.time}`;
                        if (s.note) scheduleHtml += ` <em>${s.note}</em>`;
                        li.innerHTML = scheduleHtml;
                        ul.appendChild(li);
                    });
                    cellSchedule.appendChild(ul);
                });
            } else {
                const row = trainingTimesBody.insertRow();
                const cell = row.insertCell();
                cell.colSpan = 2;
                cell.textContent = 'Trainingsuren informatie is momenteel niet beschikbaar.';
                cell.style.textAlign = 'center';
            }
            if (data.contacts && data.contacts.length > 0) {
                data.contacts.forEach(contact => {
                    const h2 = document.createElement('h2');
                    h2.textContent = contact.role;
                    contactsContainer.appendChild(h2);
                    const personDiv = document.createElement('div');
                    personDiv.className = 'person-info';
                    if (contact.image) {
                        const img = document.createElement('img');
                        img.src = contact.image;
                        img.alt = contact.imageAlt || `Foto ${contact.name}`;
                        personDiv.appendChild(img);
                    }
                    const pName = document.createElement('p');
                    const strongName = document.createElement('strong');
                    strongName.textContent = contact.name;
                    pName.appendChild(strongName);
                    personDiv.appendChild(pName);
                    if (contact.email) {
                        const pEmail = document.createElement('p');
                        pEmail.innerHTML = `E-mail: <a href="mailto:${contact.email}">${contact.email}</a>`;
                        personDiv.appendChild(pEmail);
                    }
                    if (contact.phone) {
                        const pPhone = document.createElement('p');
                        pPhone.textContent = `Tel: ${contact.phone}`;
                        personDiv.appendChild(pPhone);
                    }
                    contactsContainer.appendChild(personDiv);
                });
            }
            let trainerGroups = [];
            if (Array.isArray(data.trainer_category_order) && data.trainerGroups) {
                data.trainer_category_order.forEach(name => {
                    const group = data.trainerGroups.find(g => g.groupName === name);
                    if (group) trainerGroups.push(group);
                });
                data.trainerGroups.forEach(g => {
                    if (!trainerGroups.includes(g)) trainerGroups.push(g);
                });
            } else {
                trainerGroups = data.trainerGroups || [];
            }
            if (trainerGroups.length > 0) {
                trainerGroups.forEach(group => {
                    const groupContainer = document.createElement('div');
                    groupContainer.className = 'image-layout-container';
                    const h2 = document.createElement('h2');
                    h2.textContent = group.groupName;
                    groupContainer.appendChild(h2);
                    const flexWrapper = document.createElement('div');
                    flexWrapper.className = 'flex-content-wrapper';
                    const imageCenterDiv = document.createElement('div');
                    imageCenterDiv.className = 'image-center';
                    if (group.mainPhoto && group.mainPhoto.src) {
                        const mainImg = document.createElement('img');
                        mainImg.className = 'main-photo';
                        mainImg.src = group.mainPhoto.src;
                        mainImg.alt = group.mainPhoto.alt || `Hoofdfoto ${group.groupName}`;
                        mainImg.addEventListener('click', window.openTrainerImageInLightbox);
                        imageCenterDiv.appendChild(mainImg);
                    }
                    if (group.thumbnails && group.thumbnails.length > 0) {
                        const extraContentDiv = document.createElement('div');
                        extraContentDiv.className = 'extra-content-below';
                        group.thumbnails.forEach(thumb => {
                            const thumbImg = document.createElement('img');
                            thumbImg.className = 'thumbnail';
                            thumbImg.src = thumb.src;
                            thumbImg.alt = thumb.alt || `Thumbnail ${group.groupName}`;
                            thumbImg.addEventListener('click', window.openTrainerImageInLightbox);
                            extraContentDiv.appendChild(thumbImg);
                        });
                        imageCenterDiv.appendChild(extraContentDiv);
                    }
                    flexWrapper.appendChild(imageCenterDiv);
                    const textDescriptionDiv = document.createElement('div');
                    textDescriptionDiv.className = 'text-description text-right';
                    const pDesc = document.createElement('p');
                    pDesc.innerHTML = group.description;
                    textDescriptionDiv.appendChild(pDesc);
                    if (group.trainers && group.trainers.length > 0) {
                        const h3Trainers = document.createElement('h3');
                        h3Trainers.textContent = `Trainers ${group.groupName}:`;
                        textDescriptionDiv.appendChild(h3Trainers);
                        const ulTrainers = document.createElement('ul');
                        group.trainers.forEach(trainer => {
                            const liTrainer = document.createElement('li');
                            let trainerHtml = escapeHtml(trainer.name);
                            if (trainer.email) trainerHtml += ` : <a href="mailto:${escapeHtml(trainer.email)}">${escapeHtml(trainer.email)}</a>`;
                            if (trainer.phone) trainerHtml += ` | ${escapeHtml(trainer.phone)}`;
                            liTrainer.innerHTML = trainerHtml;
                            ulTrainers.appendChild(liTrainer);
                        });
                        textDescriptionDiv.appendChild(ulTrainers);
                    }
                    flexWrapper.appendChild(textDescriptionDiv);
                    groupContainer.appendChild(flexWrapper);
                    trainerGroupsContainer.appendChild(groupContainer);
                });
            } else {
                trainerGroupsContainer.innerHTML = '<p style="text-align:center;">Informatie over trainergroepen is momenteel niet beschikbaar.</p>';
            }
        })
        .catch(error => {
            console.error('Error loading or processing trainers data:', error);
            trainingTimesBody.innerHTML = '<tr><td colspan="2" style="text-align:center; color:red;">Kon trainingsuren niet laden.</td></tr>';
            contactsContainer.innerHTML = '<p style="text-align:center; color:red;">Kon contactinformatie niet laden.</p>';
            trainerGroupsContainer.innerHTML = '<p style="text-align:center; color:red;">Kon trainergroepen niet laden.</p>';
        });
    function escapeHtml(unsafe) {
        if (unsafe === null || typeof unsafe === 'undefined') return '';
        return unsafe.toString().replace(/&/g, "&").replace(/</g, "<").replace(/>/g, ">").replace(/"/g, '"').replace(/'/g, "'");
    }
});
