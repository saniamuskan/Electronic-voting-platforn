
const credentialForm = document.getElementById("credential-form");
const credentialButton = document.getElementById("credential-button");
const credentialResult = document.getElementById("credential-result");
const credentialValue = document.getElementById("credential-value");

const ballotPanel = document.getElementById("ballot-panel");
const confirmationPanel = document.getElementById("confirmation-panel");
const completionPanel = document.getElementById("completion-panel");

const continueButton = document.getElementById("continue-button");
const reviewButton = document.getElementById("review-button");
const backButton = document.getElementById("back-button");
const submitButton = document.getElementById("submit-button");

const notice = document.getElementById("notice");
const progressCount = document.getElementById("progress-count");
const selectionSummary = document.getElementById("selection-summary");

let votingCredential = null;
let selectedCandidate = null;
let submissionComplete = false;

function showNotice(message, type = "info") {
    notice.textContent = message;
    notice.className = `notice ${type}`;
    notice.hidden = false;
}

function clearNotice() {
    notice.hidden = true;
    notice.textContent = "";
    notice.className = "notice";
}

function updateProgress(step) {
    progressCount.textContent = `Step ${step} of 3`;

    for (let number = 1; number <= 3; number++) {
        const indicator = document.getElementById(
            `step-indicator-${number}`
        );

        indicator.classList.toggle("active", number === step);
        indicator.classList.toggle("complete", number < step);

        const numberElement = indicator.querySelector(".step-number");
        numberElement.textContent = number < step ? "✓" : number;
    }
}

async function readResponse(response) {
    let data;

    try {
        data = await response.json();
    } catch {
        throw new Error("The server returned an invalid response.");
    }

    if (!response.ok) {
        throw new Error(data.error || "The request could not be completed.");
    }

    return data;
}

// STEP 1: Request a credential from the Flask API.
credentialForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearNotice();

    const voterReference = document
        .getElementById("voter-reference")
        .value.trim();

    if (!voterReference) {
        showNotice("Please enter your voter reference.", "error");
        return;
    }

    credentialButton.disabled = true;
    credentialButton.textContent = "Requesting credential...";

    try {
        const response = await fetch("/api/credentials/issue", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                voter_reference: voterReference
            })
        });

        const data = await readResponse(response);

        if (!data.credential) {
            throw new Error("The server did not return a credential.");
        }

        votingCredential = data.credential;
        credentialValue.value = votingCredential;
        credentialValue.type = "password";

        credentialResult.hidden = false;
        credentialForm.hidden = true;

        showNotice(
            "Credential issued successfully. Keep it private and continue to the ballot.",
            "success"
        );
    } catch (error) {
        showNotice(error.message, "error");
    } finally {
        credentialButton.disabled = false;
        credentialButton.innerHTML =
            'Request credential <span aria-hidden="true">→</span>';
    }
});

// Show or hide the credential on the screen.
document.getElementById("toggle-credential").addEventListener("click", (event) => {
    const isHidden = credentialValue.type === "password";

    credentialValue.type = isHidden ? "text" : "password";
    event.currentTarget.textContent = isHidden ? "Hide" : "Show";
    event.currentTarget.setAttribute(
        "aria-label",
        isHidden ? "Hide credential" : "Show credential"
    );
});

// Copy the credential when the browser permits clipboard access.
document.getElementById("copy-credential").addEventListener("click", async () => {
    if (!votingCredential) return;

    try {
        await navigator.clipboard.writeText(votingCredential);
        showNotice("Credential copied to clipboard.", "success");
    } catch {
        showNotice(
            "Clipboard access is unavailable. You can reveal and copy the credential manually.",
            "error"
        );
    }
});

// STEP 2: Unlock the ballot only after a credential is issued.
continueButton.addEventListener("click", () => {
    if (!votingCredential || submissionComplete) {
        showNotice("Request a valid credential before continuing.", "error");
        return;
    }

    ballotPanel.classList.remove("locked-panel");
    document.getElementById("ballot-lock").hidden = true;

    document.querySelectorAll('input[name="candidate"]').forEach((input) => {
        input.disabled = false;
    });

    updateProgress(2);
    ballotPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    showNotice("Choose one candidate to continue.", "info");
});

// Update the selection summary as the voter selects a candidate.
document.querySelectorAll('input[name="candidate"]').forEach((input) => {
    input.addEventListener("change", () => {
        selectedCandidate = input.value;

        const card = input.closest(".candidate-card");
        const name = card.querySelector(".candidate-info strong").textContent;

        selectionSummary.textContent = `Your current selection: ${name}. You can change it before submission.`;
        reviewButton.disabled = false;
        clearNotice();
    });
});

// STEP 3: Review the selection before submitting.
reviewButton.addEventListener("click", () => {
    if (!votingCredential || !selectedCandidate || submissionComplete) {
        showNotice("Please obtain a credential and select a candidate.", "error");
        return;
    }

    const selectedInput = document.querySelector(
        'input[name="candidate"]:checked'
    );

    if (!selectedInput) {
        showNotice("Please select one candidate.", "error");
        return;
    }

    const candidateName = selectedInput
        .closest(".candidate-card")
        .querySelector(".candidate-info strong")
        .textContent;

    document.getElementById("final-candidate").textContent = candidateName;

    confirmationPanel.hidden = false;
    updateProgress(3);
    clearNotice();

    confirmationPanel.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
});

// Return to the ballot if the voter wants to change the selection.
backButton.addEventListener("click", () => {
    confirmationPanel.hidden = true;
    updateProgress(2);

    ballotPanel.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
});

// Submit the encrypted ballot through the Flask API.
submitButton.addEventListener("click", async () => {
    if (!votingCredential || !selectedCandidate || submissionComplete) {
        showNotice("The ballot cannot be submitted in its current state.", "error");
        return;
    }

    const confirmed = window.confirm(
        "Are you sure you want to submit this vote? Your credential will be consumed."
    );

    if (!confirmed) return;

    submitButton.disabled = true;
    submitButton.textContent = "Submitting ballot...";

    try {
        const response = await fetch("/api/ballots", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                credential: votingCredential,
                vote: {
                    candidate: selectedCandidate
                }
            })
        });

        const data = await readResponse(response);

        submissionComplete = true;

        // Remove the secret from the page and the JavaScript variable.
        votingCredential = null;
        credentialValue.value = "";
        credentialValue.type = "password";

        ballotPanel.hidden = true;
        confirmationPanel.hidden = true;
        document.getElementById("credential-panel").hidden = true;
        completionPanel.hidden = false;

        document.getElementById("completion-message").textContent =
            data.message || "The server accepted your ballot.";

        updateProgress(3);
        clearNotice();

        completionPanel.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    } catch (error) {
        showNotice(
            `${error.message} If the network failed after submission, check the ballot status before trying again.`,
            "error"
        );
    } finally {
        if (!submissionComplete) {
            submitButton.disabled = false;
            submitButton.textContent = "Confirm and submit";
        }
    }
});

updateProgress(1);
