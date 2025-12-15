// ==========================================
// 1. FILE UPLOAD VISUALS
// ==========================================
function handleFileSelect(elementId, input) {
    const dropzone = document.getElementById(elementId);
    if (input.files && input.files.length > 0) {
        dropzone.classList.add('uploaded');
        dropzone.querySelector('.file-label').innerHTML = `
            <span style="color:#22c55e; font-weight:bold;">✅ ${input.files[0].name}</span>
        `;
    }
}

// ==========================================
// 2. MAIN ANALYSIS LOGIC
// ==========================================
document.getElementById('analyzeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // UI Elements
    const btn = document.getElementById('runBtn');
    const initialState = document.getElementById('initialState');
    const processingState = document.getElementById('processingState');
    const iframe = document.getElementById('reportFrame');
    
    // Files
    const refFile = document.getElementById('refFile').files[0];
    const currFile = document.getElementById('currFile').files[0];

    if (!refFile || !currFile) {
        alert("⚠️ System Alert: Both datasets required.");
        return;
    }

    // Start Animation
    btn.disabled = true;
    initialState.style.display = 'none';
    iframe.style.display = 'none';
    processingState.style.display = 'flex';
    processingState.classList.remove('hidden');

    const formData = new FormData();
    formData.append('reference_file', refFile);
    formData.append('current_file', currFile);

    try {
        const response = await fetch('/api/analyze', { method: 'POST', body: formData });
        const result = await response.json();
        
        // --- 1. HANDLE DATA CONTRACT VIOLATION ---
        if (response.status === 400) {
            alert("❌ DATA CONTRACT VIOLATION:\n" + result.detail.errors.join("\n"));
            // Reset UI
            btn.disabled = false;
            processingState.style.display = 'none';
            initialState.style.display = 'flex';
            return;
        }

        if (result.status === 'success') {
            setTimeout(() => {
                processingState.style.display = 'none';
                iframe.classList.remove('hidden');
                iframe.style.display = 'block';
                
                // Inject HTML Report
                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                iframeDoc.open();
                iframeDoc.write(result.data.html_report);
                iframeDoc.close();
                
                // Update Enterprise Dashboard
                updateDashboard(result.data);
                
                btn.disabled = false;
            }, 1000); 
        } else {
            throw new Error(result.message || "Analysis Failed");
        }
    } catch (err) {
        console.error(err);
        alert("❌ Error: " + err.message);
        processingState.style.display = 'none';
        initialState.style.display = 'flex';
        btn.disabled = false;
    }
});

// ==========================================
// 3. ENTERPRISE VISUALIZATION
// ==========================================
function updateDashboard(data) {
    // Reveal Cards
    document.getElementById('riskCard').classList.remove('hidden');
    document.getElementById('leaderboardCard').classList.remove('hidden');

    // 1. AUTOMATION & RULES
    const actionBadge = document.getElementById('actionBadge');
    actionBadge.innerText = data.automation.action;
    actionBadge.style.color = data.automation.color;
    actionBadge.style.textShadow = `0 0 15px ${data.automation.color}40`;

    document.getElementById('actionDesc').innerHTML = `
        <span style="color:#fff; font-weight:bold;">RULE: ${data.automation.rule}</span><br>
        ${data.automation.details}<br>
        <div style="background:rgba(255,255,255,0.05); padding:8px; border-radius:6px; margin-top:8px; font-size:0.7rem; color:#94a3b8; border-left:2px solid ${data.automation.color};">
            ⚡ <b>PIPELINE:</b> ${data.automation.pipeline}<br>
            📅 <b>STRATEGY:</b> ${data.automation.strategy}
        </div>
    `;

    // 2. FINANCIALS
    const revRisk = document.getElementById('revenueRisk');
    revRisk.innerText = data.financials.risk_amount;
    revRisk.parentElement.title = data.financials.disclaimer;

    // 3. STATS & FAIRNESS (Deep Dive)
    console.group("📊 DATA SCIENCE DEEP DIVE");
    
    // Fairness Logic
    const businessScoreEl = document.getElementById('businessScore');
    
    if (data.rigor.fairness && data.rigor.fairness.length > 0) {
        // Red Text in Console
        console.log("%c⚠️ FAIRNESS AUDIT FAILED", "color: #ff0055; font-weight:bold; font-size: 14px;");
        data.rigor.fairness.forEach(f => {
            console.log(`Protected Group [${f.group}]: Disparity ${f.disparity} (Target < 0.8)`);
        });
        // Update Score Card UI to warn user
        businessScoreEl.innerHTML = `<span style="color:#ff0055; font-weight:bold;">BIAS DETECTED</span>`;
    } else {
        console.log("%c✅ Fairness Audit Passed", "color: #22c55e; font-size: 12px;");
        // Standard reliability score
        businessScoreEl.innerHTML = `
            <span style="color:${data.model_health.reliability === 'STABLE' ? '#22c55e' : '#ef4444'}">${data.model_health.reliability}</span><br>
            <span style="font-size:0.65rem; color:#94a3b8;">Est. F1: ${data.model_health.est_f1_drop}</span>
        `;
    }

    // P-Values Logic
    console.log("--------------------------------");
    console.log("📈 Statistical Significance (KS-Test p < 0.05)");
    if(data.rigor.p_values.length === 0) {
        console.log("No statistically significant drift detected.");
    } else {
        data.rigor.p_values.forEach(p => {
            console.log(`Feature: ${p.feature.padEnd(20)} | p-value: ${p.p_value}`);
        });
    }
    console.groupEnd();

    // 4. LEADERBOARD
    const list = document.getElementById('lbList');
    list.innerHTML = ''; 
    
    data.leaderboard.forEach(item => {
        const li = document.createElement('li');
        let color = '#22c55e'; // Green
        if(item.impact_tag === 'CRITICAL') color = '#ff0055'; // Neon Red
        else if(item.impact_tag === 'HIGH') color = '#f59e0b'; // Orange
        
        li.style.borderLeft = `3px solid ${color}`;
        
        li.innerHTML = `
            <div style="display:flex; justify-content:space-between; width:100%;">
                <div style="display:flex; flex-direction:column;">
                    <span style="font-weight:600; color:white; font-size:0.8rem; display:flex; align-items:center; gap:5px;">
                        ${item.feature}
                        <span style="background:${color}; color:white; padding:1px 4px; border-radius:3px; font-size:0.5rem;">
                            ${item.impact_tag}
                        </span>
                    </span>
                    <span style="font-size:0.65rem; color:#94a3b8; margin-top:2px;">
                        👉 ${item.suggested_action}
                    </span>
                </div>
                <div style="text-align:right;">
                     <span style="font-weight:bold; color:${item.detected ? color : '#22c55e'}">
                        ${item.score.toFixed(2)}
                    </span>
                </div>
            </div>
        `;
        list.appendChild(li);
    });
}