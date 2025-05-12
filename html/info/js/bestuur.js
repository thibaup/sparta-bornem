document.addEventListener('DOMContentLoaded', function() {
    const jsonPath = '../info/json/bestuur.json';
    const container = document.querySelector('main.main-content.container');
    const pageTitleElement = document.getElementById('page-title');
    const mainHeadingElement = document.getElementById('main-heading');

    if (!container) {
        console.error('Container not found.');
        return;
    }

    fetch(jsonPath)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.pageTitle && pageTitleElement) {
                pageTitleElement.textContent = data.pageTitle;
            }
            if (data.mainHeading && mainHeadingElement) {
                mainHeadingElement.textContent = data.mainHeading;
            }

            if (data.boardMembers && data.boardMembers.length > 0) {
                data.boardMembers.forEach(member => {
                    const memberDiv = document.createElement('div');
                    memberDiv.className = 'board-member';

                    if (member.imageSrc) {
                        const img = document.createElement('img');
                        img.src = member.imageSrc;
                        img.alt = member.imageAlt || member.name;
                        memberDiv.appendChild(img);
                    }

                    const nameH3 = document.createElement('h3');
                    nameH3.textContent = member.name;
                    memberDiv.appendChild(nameH3);

                    if (member.role) {
                        const roleSpan = document.createElement('span');
                        roleSpan.className = 'role';
                        roleSpan.textContent = member.role;
                        memberDiv.appendChild(roleSpan);
                    }

                    if (member.address) {
                        const pAddress = document.createElement('p');
                        pAddress.textContent = `Adres: ${member.address}`;
                        memberDiv.appendChild(pAddress);
                    }

                    if (member.phone) {
                        const pPhone = document.createElement('p');
                        pPhone.textContent = `Gsm: ${member.phone}`;
                        memberDiv.appendChild(pPhone);
                    }

                    if (member.email) {
                        const pEmail = document.createElement('p');
                        const emailLink = document.createElement('a');
                        emailLink.href = `mailto:${member.email}`;
                        emailLink.textContent = member.email;
                        pEmail.appendChild(document.createTextNode('E-mail: '));
                        pEmail.appendChild(emailLink);
                        memberDiv.appendChild(pEmail);
                    }

                    container.appendChild(memberDiv);
                });
            } else {
                container.innerHTML = '<p>Geen bestuursleden gevonden.</p>';
            }
        })
        .catch(error => {
            console.error('Error loading or processing bestuur data:', error);
            container.innerHTML = '<p style="color: red;">Kon bestuursinformatie niet laden.</p>';
        });
});