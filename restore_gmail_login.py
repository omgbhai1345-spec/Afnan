from pathlib import Path
path = Path(r'\\CHS-31\files\Dillu\new.html')
text = path.read_text(encoding='utf-8')

insert_after = "btn.disabled = false;\n    btn.innerHTML = '<i class=\"ri-login-circle-line\"></i> Sign In';\n}\n\n"
if insert_after not in text:
    raise RuntimeError('handleLogin end block not found')

new_block = """btn.disabled = false;
    btn.innerHTML = '<i class=\"ri-login-circle-line\"></i> Sign In';
}

function handleGoogleSheetLogin() {
    let email = document.getElementById('loginEmail').value.trim();
    const errorDiv = document.getElementById('loginError');
    errorDiv.style.display = 'none';
    if (!email) {
        email = prompt('Enter your Gmail address to login as a student:');
        if (!email) {
            errorDiv.style.display = 'block';
            document.getElementById('errorMessage').textContent = 'Student Gmail is required.';
            showToast('Gmail required', 'warning');
            return;
        }
    }
    currentRole = 'student';
    const btn = document.getElementById('loginBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class=\"spinner\"></span> Validating...';
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
        btn.innerHTML = '<i class=\"ri-login-circle-line\"></i> Sign In';
    });
}

"""
text = text.replace(insert_after, new_block)
path.write_text(text, encoding='utf-8')
print('restored Gmail login handler')
