from pathlib import Path
path = Path(r'\\CHS-31\files\Dillu\new.html')
text = path.read_text(encoding='utf-8')

# Remove Google Identity SDK script reference
text = text.replace(
    '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>\n    <script src="https://accounts.google.com/gsi/client" async defer></script>',
    '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'
)

# Update email field placeholder to optional
text = text.replace(
    '                    <input type="email" class="form-input" id="loginEmail" placeholder="Enter your email">',
    '                    <input type="email" class="form-input" id="loginEmail" placeholder="Enter your Gmail address (optional)">'
)

# Remove googleRenderContainer block
text = text.replace(
    '            <div class="form-group" id="googleRenderContainer" style="display:none;">\n                <div id="googleSignInButton"></div>\n            </div>',
    ''
)

# Replace handleGoogleSheetLogin function with a prompt-based Gmail login
old = '''function handleGoogleSheetLogin() {
    if (window.google && google.accounts && google.accounts.id) {
        google.accounts.id.prompt();
        return;
    }
    const email = document.getElementById('loginEmail').value.trim();
    const errorDiv = document.getElementById('loginError');
    errorDiv.style.display = 'none';
    if (!email) {
        errorDiv.style.display = 'block';
        document.getElementById('errorMessage').textContent = 'Google login is not ready. Please refresh and allow Google login or enter your Gmail address.';
        showToast('Google login not available', 'warning');
        return;
    }
    currentRole = 'student';
    const btn = document.getElementById('loginBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Validating...';
    validateStudentWithSheet(email).then(user => {
        if (user) {
            currentUser = user;
            document.getElementById('loginPage').style.display = 'none';
            document.getElementById('appContainer').classList.add('active');
            showToast(`Welcome, ${user.name}!`, 'success');
            initApp(user);
        } else {
            errorDiv.style.display = 'block';
            document.getElementById('errorMessage').textContent = 'Student Gmail not found in Google Sheet.';
            showToast('Google Sheet login failed', 'error');
        }
        btn.disabled = false;
        btn.innerHTML = '<i class="ri-login-circle-line"></i> Sign In';
    });
}
'''
replace = '''function handleGoogleSheetLogin() {
    let email = document.getElementById('loginEmail').value.trim();
    const errorDiv = document.getElementById('loginError');
    errorDiv.style.display = 'none';
    if (!email) {
        email = prompt('Please enter your Gmail address for student login');
        if (!email) {
            errorDiv.style.display = 'block';
            document.getElementById('errorMessage').textContent = 'Student Gmail is required to login.';
            showToast('Gmail required', 'warning');
            return;
        }
    }
    currentRole = 'student';
    const btn = document.getElementById('loginBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Validating...';
    validateStudentWithSheet(email).then(user => {
        if (user) {
            currentUser = user;
            document.getElementById('loginPage').style.display = 'none';
            document.getElementById('appContainer').classList.add('active');
            showToast(`Welcome, ${user.name}!`, 'success');
            initApp(user);
        } else {
            errorDiv.style.display = 'block';
            document.getElementById('errorMessage').textContent = 'Student Gmail not found in Google Sheet.';
            showToast('Gmail login failed', 'error');
        }
        btn.disabled = false;
        btn.innerHTML = '<i class="ri-login-circle-line"></i> Sign In';
    });
}
'''
if old not in text:
    raise RuntimeError('Old handleGoogleSheetLogin function not found')
text = text.replace(old, replace)

# Remove leftover Google sign-in helper functions and event listener
start = text.find('const GOOGLE_CLIENT_ID =')
if start != -1:
    end = text.find('window.addEventListener(\'DOMContentLoaded\'', start)
    if end != -1:
        end = text.find('function handleLogout()', end)
        if end != -1:
            text = text[:start] + text[end:]
        else:
            raise RuntimeError('Could not find function handleLogout after Google sign-in code')

# Make admin login invisible-only for admin role by keeping email input optional
# no more Google SDK required
path.write_text(text, encoding='utf-8')
print('cleaned Google login and simplified Gmail student login')
