document.addEventListener('DOMContentLoaded', () => {
  const jsonPath = '../info/json/juryleden.json';
  const container = document.querySelector('main.main-content.container');
  const pageTitleElement = document.getElementById('page-title');
  const mainHeadingElement = document.getElementById('main-heading');
  if (!container) return;

  const load = async () => {
    try {
      const response = await fetch(jsonPath, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();

      if (data.pageTitle && pageTitleElement) pageTitleElement.textContent = data.pageTitle;
      if (data.mainHeading && mainHeadingElement) mainHeadingElement.textContent = data.mainHeading;

      const members = Array.isArray(data.juryMembers) ? data.juryMembers : [];
      if (members.length === 0) {
        container.innerHTML = '<p>Geen juryleden gevonden.</p>';
        return;
      }

      members.forEach(member => {
        const div = document.createElement('div');
        div.className = 'board-member';

        if (member.imageSrc) {
          const img = document.createElement('img');
          img.src = member.imageSrc;
          img.alt = member.imageAlt || member.name || 'Jurylid';
          div.appendChild(img);
        }

        const nameH3 = document.createElement('h3');
        nameH3.textContent = member.name || 'Onbekend';
        div.appendChild(nameH3);

        if (member.role) {
          const roleSpan = document.createElement('span');
          roleSpan.className = 'role';
          roleSpan.textContent = member.role;
          div.appendChild(roleSpan);
        }

        if (member.address) {
          const p = document.createElement('p');
          p.textContent = `Adres: ${member.address}`;
          div.appendChild(p);
        }

        if (member.phone) {
          const p = document.createElement('p');
          p.textContent = `Gsm: ${member.phone}`;
          div.appendChild(p);
        }

        if (member.email) {
          const p = document.createElement('p');
          const a = document.createElement('a');
          a.href = `mailto:${member.email}`;
          a.textContent = member.email;
          p.appendChild(document.createTextNode('E-mail: '));
          p.appendChild(a);
          div.appendChild(p);
        }

        container.appendChild(div);
      });
    } catch (error) {
      console.error('Error loading or processing juryleden data:', error);
      container.innerHTML = '<p style="color: red;">Kon jury-informatie niet laden.</p>';
    }
  };

  load();
});
