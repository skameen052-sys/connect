package com.example.arshithconnectattendance;

import android.Manifest;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.text.TextUtils;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ProgressBar;
import android.widget.Toast;

import androidx.activity.ComponentActivity;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.core.content.ContextCompat;

import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.firestore.DocumentSnapshot;
import com.google.firebase.firestore.FirebaseFirestore;
import com.google.firebase.firestore.QuerySnapshot;
import com.google.firebase.messaging.FirebaseMessaging;

public class MainActivity extends ComponentActivity {

    private static final String PREFS_NAME = "ArshithConnectPrefs";
    private static final String KEY_LOGIN_TYPE = "loginType";
    private static final String TAG = "ArshithFCM";

    private EditText etEmail;
    private EditText etPassword;
    private Button btnLogin;
    private Button btnOpenAdminLogin;
    private Button btnRegister;
    private ProgressBar progressBar;

    private FirebaseAuth firebaseAuth;
    private FirebaseFirestore firestore;

    private final ActivityResultLauncher<String> notificationPermissionLauncher =
            registerForActivityResult(
                    new ActivityResultContracts.RequestPermission(),
                    isGranted -> {
                        if (isGranted) {
                            Log.d(TAG, "Notification permission granted.");
                            saveFcmToken();
                        } else {
                            Log.w(TAG, "Notification permission denied.");
                        }
                    });

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        try {
            firebaseAuth = FirebaseAuth.getInstance();
            firestore = FirebaseFirestore.getInstance();
            setContentView(R.layout.activity_main);

            initializeViews();
            setupClickListeners();

            FirebaseUser currentUser = firebaseAuth.getCurrentUser();
            SharedPreferences preferences = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
            String loginType = preferences.getString(KEY_LOGIN_TYPE, "");

            if (currentUser != null) {
                if ("EMPLOYEE".equals(loginType)) {
                    checkEmployeeApproval(currentUser, false);
                    return;
                }

                if ("ADMIN".equals(loginType)) {
                    startActivity(new Intent(MainActivity.this, AdminDashboardActivity.class));
                    finish();
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Error in MainActivity onCreate", e);
            Toast.makeText(this, "Welcome to Arshith Connect. Please log in.", Toast.LENGTH_SHORT).show();
        }
    }

    private void initializeViews() {
        etEmail = findViewById(R.id.etEmail);
        etPassword = findViewById(R.id.etPassword);
        btnLogin = findViewById(R.id.btnLogin);
        btnOpenAdminLogin = findViewById(R.id.btnOpenAdminLogin);
        btnRegister = findViewById(R.id.btnRegister);
        progressBar = findViewById(R.id.progressBar);
    }

    private void setupClickListeners() {
        btnLogin.setOnClickListener(v -> loginUser());

        btnOpenAdminLogin.setOnClickListener(v ->
                startActivity(new Intent(MainActivity.this, AdminLoginActivity.class)));

        btnRegister.setOnClickListener(v ->
                startActivity(new Intent(MainActivity.this, RegisterActivity.class)));
    }

    private void loginUser() {
        String email = etEmail.getText().toString().trim();
        String password = etPassword.getText().toString().trim();

        if (TextUtils.isEmpty(email)) {
            etEmail.setError("Please enter your email");
            etEmail.requestFocus();
            return;
        }
        if (TextUtils.isEmpty(password)) {
            etPassword.setError("Please enter your password");
            etPassword.requestFocus();
            return;
        }

        showLoading(true);
        try {
            firebaseAuth.signInWithEmailAndPassword(email, password)
                    .addOnCompleteListener(this, task -> {
                        if (!task.isSuccessful()) {
                            showLoading(false);
                            String message = task.getException() != null
                                    && !TextUtils.isEmpty(task.getException().getMessage())
                                    ? task.getException().getMessage()
                                    : "Login failed. Please try again.";
                            Toast.makeText(this, message, Toast.LENGTH_LONG).show();
                            return;
                        }

                        FirebaseUser user = firebaseAuth.getCurrentUser();
                        if (user == null) {
                            showLoading(false);
                            Toast.makeText(this, "Unable to get user account.", Toast.LENGTH_LONG).show();
                            return;
                        }
                        checkEmployeeApproval(user, true);
                    });
        } catch (Exception e) {
            Log.e(TAG, "Exception during sign in", e);
            showLoading(false);
            Toast.makeText(this, "Sign-in error: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    /**
     * Checks the employee record by Firebase UID first. For older registrations
     * whose Firestore document ID is not the Firebase UID, it falls back to an
     * exact email match in the employees collection.
     */
    private void checkEmployeeApproval(FirebaseUser user, boolean showLoginSuccess) {
        if (user == null) {
            showLoading(false);
            Toast.makeText(this, "Unable to verify your account.", Toast.LENGTH_LONG).show();
            return;
        }

        showLoading(true);
        try {
            firestore.collection("employees").document(user.getUid()).get()
                    .addOnSuccessListener(document -> {
                        if (isFinishing() || isDestroyed()) return;

                        if (document.exists()) {
                            handleEmployeeDocument(document, user, showLoginSuccess);
                        } else {
                            findEmployeeByEmail(user, showLoginSuccess);
                        }
                    })
                    .addOnFailureListener(e -> {
                        Log.e(TAG, "Employee UID lookup failed.", e);
                        if (!isFinishing() && !isDestroyed()) {
                            showLoading(false);
                            Toast.makeText(this,
                                    "Could not verify your approval. Check your connection and try again.",
                                    Toast.LENGTH_LONG).show();
                        }
                    });
        } catch (Exception e) {
            Log.e(TAG, "Exception checking employee approval", e);
            if (!isFinishing() && !isDestroyed()) {
                showLoading(false);
                Toast.makeText(this, "Could not verify your account. Please check your connection.", Toast.LENGTH_LONG).show();
            }
        }
    }

    private void findEmployeeByEmail(FirebaseUser user, boolean showLoginSuccess) {
        String email = user.getEmail();
        if (TextUtils.isEmpty(email)) {
            denyEmployeeAccess("Employee registration was not found. Please contact the administrator.");
            return;
        }

        try {
            firestore.collection("employees").whereEqualTo("email", email).limit(2).get()
                    .addOnSuccessListener(snapshot -> {
                        if (isFinishing() || isDestroyed()) return;

                        if (snapshot.isEmpty()) {
                            denyEmployeeAccess("Employee registration was not found. Please contact the administrator.");
                            return;
                        }

                        if (snapshot.size() > 1) {
                            showLoading(false);
                            Toast.makeText(this,
                                    "Multiple employee records use this email. Please contact the administrator.",
                                    Toast.LENGTH_LONG).show();
                            return;
                        }

                        DocumentSnapshot employeeDocument = snapshot.getDocuments().get(0);
                        handleEmployeeDocument(employeeDocument, user, showLoginSuccess);
                    })
                    .addOnFailureListener(e -> {
                        Log.e(TAG, "Employee email lookup failed.", e);
                        if (!isFinishing() && !isDestroyed()) {
                            showLoading(false);
                            Toast.makeText(this,
                                    "Could not find your employee record. Please check your connection or contact the administrator.",
                                    Toast.LENGTH_LONG).show();
                        }
                    });
        } catch (Exception e) {
            Log.e(TAG, "Exception finding employee by email", e);
            if (!isFinishing() && !isDestroyed()) {
                showLoading(false);
                Toast.makeText(this, "Could not lookup employee record. Please check your connection.", Toast.LENGTH_LONG).show();
            }
        }
    }

    private void handleEmployeeDocument(DocumentSnapshot document,
                                        FirebaseUser user,
                                        boolean showLoginSuccess) {
        String storedEmail = document.getString("email");
        String authEmail = user.getEmail();
        if (!TextUtils.isEmpty(storedEmail) && !TextUtils.isEmpty(authEmail)
                && !storedEmail.trim().equalsIgnoreCase(authEmail.trim())) {
            denyEmployeeAccess("The employee record does not match this login. Please contact the administrator.");
            return;
        }

        String status = document.getString("status");
        if (status == null) {
            denyEmployeeAccess("Your account has not been approved. Please contact the administrator.");
            return;
        }

        status = status.trim();
        if ("pending".equalsIgnoreCase(status)) {
            denyEmployeeAccess("Your registration is awaiting admin approval.");
            return;
        }
        if ("rejected".equalsIgnoreCase(status)) {
            denyEmployeeAccess("Your registration was rejected. Please contact the administrator.");
            return;
        }
        if (!"approved".equalsIgnoreCase(status) && !"active".equalsIgnoreCase(status)) {
            denyEmployeeAccess("Your account status is not approved. Please contact the administrator.");
            return;
        }

        getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit()
                .putString(KEY_LOGIN_TYPE, "EMPLOYEE")
                .apply();

        showLoading(false);
        if (showLoginSuccess) {
            Toast.makeText(this, "Login successful", Toast.LENGTH_SHORT).show();
        }
        askNotificationPermission();
        startActivity(new Intent(MainActivity.this, EmployeeDashboardActivity.class));
        finish();
    }

    private void denyEmployeeAccess(String message) {
        showLoading(false);
        firebaseAuth.signOut();
        getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit()
                .remove(KEY_LOGIN_TYPE)
                .apply();
        Toast.makeText(MainActivity.this, message, Toast.LENGTH_LONG).show();
    }

    private void showLoading(boolean loading) {
        if (progressBar != null) {
            progressBar.setVisibility(loading ? View.VISIBLE : View.GONE);
        }
        if (btnLogin != null) btnLogin.setEnabled(!loading);
        if (btnOpenAdminLogin != null) btnOpenAdminLogin.setEnabled(!loading);
        if (btnRegister != null) btnRegister.setEnabled(!loading);
    }

    private void askNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS);
            } else {
                saveFcmToken();
            }
        } else {
            saveFcmToken();
        }
    }

    private void saveFcmToken() {
        try {
            FirebaseUser user = firebaseAuth.getCurrentUser();
            if (user == null) {
                Log.w(TAG, "Cannot save FCM token. User is null.");
                return;
            }

            FirebaseMessaging.getInstance().getToken()
                    .addOnSuccessListener(token -> {
                        if (TextUtils.isEmpty(token)) {
                            Log.e(TAG, "FCM token is empty.");
                            return;
                        }
                        NotificationTokenManager.saveToken(token);
                        Log.d(TAG, "FCM token submitted to Firestore.");
                    })
                    .addOnFailureListener(e -> Log.e(TAG, "FCM token generation failed.", e));
        } catch (Exception e) {
            Log.e(TAG, "Error requesting FCM token", e);
        }
    }
}
