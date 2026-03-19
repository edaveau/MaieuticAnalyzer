let selectedFile = null;

const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const fileNameDisplay = document.getElementById("fileName");

// clic
dropZone.onclick = () => fileInput.click();

// sélection classique
fileInput.onchange = (e) => {
    handleFile(e.target.files[0]);
};

// drag & drop
dropZone.addEventListener("dragover", e => {
    e.preventDefault();
});

dropZone.addEventListener("drop", e => {
    e.preventDefault();
    handleFile(e.dataTransfer.files[0]);
});

function handleFile(file) {
    if (!file) return;

    selectedFile = file;
    fileNameDisplay.innerHTML = `✅ ${file.name}`;
    dropZone.classList.add("loaded");
}

// Upload
async function upload() {

    const errorBox = document.getElementById("errorBox");
    errorBox.style.display = "none";

    if (!selectedFile) {
        showError("Veuillez sélectionner un fichier.");
        return;
    }

    if (!selectedFile.name.endsWith(".xls") && !selectedFile.name.endsWith(".xlsx")) {
        showError("Format invalide. Fichier Excel requis.");
        return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("ik", document.getElementById("ik").value);
    formData.append("if_val", document.getElementById("if_val").value);
    formData.append("md", document.getElementById("md").value);

    try {
        const res = await fetch("/upload", {
            method: "POST",
            body: formData
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Erreur serveur");
        }

        const data = await res.json();
        renderTable(data);

    } catch (err) {
        showError(err.message);
    }
}

function renderTable(data) {
    const tbody = document.querySelector("#resultTable tbody");
    tbody.innerHTML = "";

    data.forEach(row => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${row.adeli}</td>
            <td>${row.rempla || ""}</td>
            <td>${row.total}</td>
            <td>${row.indemnites}</td>
            <td>${row.retro_30}</td>
            <td>${row.retro_40}</td>
        `;

        tbody.appendChild(tr);
    });
}

function showError(msg) {
    const box = document.getElementById("errorBox");
    box.innerText = msg;
    box.style.display = "block";
}