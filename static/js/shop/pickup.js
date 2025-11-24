// =========================================
// AOS + GSAP animation initialization
// =========================================
AOS.init({ duration: 900, once: false });

gsap.from(".fade-in", {
    opacity: 0,
    y: 30,
    duration: 1,
    stagger: 0.2
});

// =========================================
// Student Search (Class or Name)
// =========================================
async function searchStudents() {
    const q = document.getElementById("searchField").value;
    const cls = document.getElementById("classFilter").value;

    let url = `/shop/pickup/search-students/?q=${q}&class=${cls}`;
    let response = await fetch(url);
    let data = await response.json();

    let box = document.getElementById("searchResults");
    box.innerHTML = "";

    if (data.results.length === 0) {
        box.innerHTML = `<p class="text-danger">No matching students found.</p>`;
        return;
    }

    data.results.forEach(st => {
        box.innerHTML += `
            <div class="result-item fade-in border p-2 mb-2 rounded" 
                 onclick="chooseStudent('${st.reg_no}', '${st.full_name}', '${st.class_name}')">
                <strong>${st.full_name}</strong> (${st.class_name})
                <br>
                <small class="text-primary">${st.reg_no}</small>
            </div>
        `;
    });
}

function chooseStudent(reg, name, cls) {
    document.getElementById("studentReg").value = reg;
    document.getElementById("selectedStudent").innerHTML = `
        <p class="alert alert-success fade-in">
            Selected: <strong>${name}</strong> (${cls}) <br>
            Reg No: <span class="fw-bold text-primary">${reg}</span>
        </p>
    `;
}

// =========================================
// Signature Pad
// =========================================
let canvas = document.getElementById("signaturePad");
let ctx = canvas.getContext("2d");
let drawing = false;

canvas.addEventListener("mousedown", () => drawing = true);
canvas.addEventListener("mouseup", () => drawing = false);
canvas.addEventListener("mousemove", draw);

function draw(e) {
    if (!drawing) return;
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.strokeStyle = "#222";
    ctx.lineTo(e.offsetX, e.offsetY);
    ctx.stroke();
}

function clearSignature() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function getSignatureData() {
    return canvas.toDataURL("image/png");
}

// =========================================
// Create Pickup Code (AJAX)
// =========================================
async function submitPickup() {
    let formData = new FormData();
    formData.append("student_reg", document.getElementById("studentReg").value);
    formData.append("bearer_name", document.getElementById("bearerName").value);
    formData.append("bearer_phone", document.getElementById("bearerPhone").value);
    formData.append("signature", getSignatureData());

    let response = await fetch("/shop/pickup/generate/", {
        method: "POST",
        body: formData,
        headers: { "X-CSRFToken": csrftoken }
    });

    let data = await response.json();

    if (data.status === "ok") {
        window.location.href = `/shop/pickup/receipt/${data.code}/`;
    } else {
        alert("Error: " + data.message);
    }
}

// =========================================
// Verify Pickup Code (Admin)
// =========================================
async function verifyCode() {
    let code = document.getElementById("verifyCodeInput").value;

    let response = await fetch(`/shop/pickup/verify/check/?code=${code}`);
    let data = await response.json();

    let box = document.getElementById("verifyResult");
    box.innerHTML = "";

    if (!data.valid) {
        box.innerHTML = `<p class="alert alert-danger">Invalid or expired code.</p>`;
        return;
    }

    box.innerHTML = `
        <div class="alert alert-success fade-in">
            <h5>Valid Pickup Code</h5>
            Student: ${data.student}
            <br> Bearer: ${data.bearer}
            <br> Phone: ${data.phone}
            <br> Status: ${data.status}
            <br>
            <a href="/shop/pickup/verify/${code}/confirm/" 
               class="btn btn-success mt-3">Confirm Pickup</a>
        </div>
    `;
}
