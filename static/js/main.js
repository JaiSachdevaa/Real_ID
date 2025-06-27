document.addEventListener("DOMContentLoaded", function () {
    const startButton = document.getElementById("start-scan");
    const scanStatus = document.getElementById("scan-status");
    const scanLine = document.getElementById("scan-line");
    const consoleBox = document.getElementById("console");
    const logList = document.getElementById("log-list");

    if (startButton) {
        startButton.addEventListener("click", function () {
            scanStatus.textContent = "Initializing scan...";
            scanLine.style.display = "block";

            fetch("/start-scan", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "scan" })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    scanStatus.textContent = "Scanning...";

                    setTimeout(() => {
                        scanStatus.textContent = "Face scanned successfully!";
                        scanLine.style.display = "none";

                        // Add log entry
                        if (logList) {
                            const logItem = document.createElement("li");
                            logItem.textContent = `Face scanned at ${new Date().toLocaleTimeString()}`;
                            logList.appendChild(logItem);
                        }

                        // Update console log
                        if (consoleBox) {
                            const consoleEntry = document.createElement("p");
                            consoleEntry.textContent = "> Face scan completed.";
                            consoleBox.appendChild(consoleEntry);
                        }
                    }, 3000);
                } else {
                    scanStatus.textContent = "Scan failed!";
                    scanLine.style.display = "none";

                    if (consoleBox) {
                        const errorEntry = document.createElement("p");
                        errorEntry.textContent = "> Scan failed: No face detected.";
                        errorEntry.style.color = "red";
                        consoleBox.appendChild(errorEntry);
                    }
                }
            })
            .catch(error => {
                scanStatus.textContent = "Scan failed!";
                scanLine.style.display = "none";
                console.error("Error during scan:", error);
                if (consoleBox) {
                    const errorEntry = document.createElement("p");
                    errorEntry.textContent = `> Error: ${error.message}`;
                    errorEntry.style.color = "red";
                    consoleBox.appendChild(errorEntry);
                }
            });
        });
    }
});
