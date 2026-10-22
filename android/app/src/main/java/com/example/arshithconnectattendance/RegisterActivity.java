
package com.example.arshithconnectattendance;

import android.content.Intent;
import android.os.Bundle;
import android.text.InputType;
import android.text.TextUtils;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.ComponentActivity;

import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.auth.UserProfileChangeRequest;
import com.google.firebase.firestore.FieldValue;
import com.google.firebase.firestore.FirebaseFirestore;

import java.util.HashMap;
import java.util.Map;

public class RegisterActivity extends ComponentActivity {

    private EditText etEmployeeName;
    private EditText etEmployeeId;
    private EditText etEmail;
    private EditText etPhone;
    private EditText etPassword;
    private EditText etConfirmPassword;

    private ImageView ivPasswordEye;
    private ImageView ivConfirmPasswordEye;

    private Button btnRegister;
    private TextView tvLogin;

    private FirebaseAuth firebaseAuth;
    private FirebaseFirestore firestore;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setContentView(R.layout.activity_register);

        // Firebase
        firebaseAuth = FirebaseAuth.getInstance();
        firestore = FirebaseFirestore.getInstance();

        // Connect XML views
        etEmployeeName = findViewById(R.id.etEmployeeName);
        etEmployeeId = findViewById(R.id.etEmployeeId);
        etEmail = findViewById(R.id.etEmail);
        etPhone = findViewById(R.id.etPhone);
        etPassword = findViewById(R.id.etPassword);
        etConfirmPassword = findViewById(R.id.etConfirmPassword);

        btnRegister = findViewById(R.id.btnRegister);
        tvLogin = findViewById(R.id.tvLogin);

        // Connect eye icons
        ivPasswordEye = findViewById(R.id.ivPasswordEye);
        ivConfirmPasswordEye = findViewById(R.id.ivConfirmPasswordEye);

        // Enable password visibility toggles
        setupPasswordVisibility(etPassword, ivPasswordEye);
        setupPasswordVisibility(etConfirmPassword, ivConfirmPasswordEye);

        // Register button
        btnRegister.setOnClickListener(v -> registerEmployee());

        // Login
        tvLogin.setOnClickListener(v -> {
            Intent intent = new Intent(
                    RegisterActivity.this,
                    MainActivity.class
            );

            startActivity(intent);
            finish();
        });
    }

    // ======================================================
    // PASSWORD VISIBILITY TOGGLE
    // ======================================================

    private void setupPasswordVisibility(
            EditText passwordField,
            ImageView eyeIcon) {

        eyeIcon.setOnClickListener(v -> {

            int selection = passwordField.getSelectionStart();

            boolean isVisible =
                    (passwordField.getInputType()
                            & InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD)
                            == InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD;

            if (isVisible) {

                // Hide password
                passwordField.setInputType(
                        InputType.TYPE_CLASS_TEXT
                                | InputType.TYPE_TEXT_VARIATION_PASSWORD
                );

                eyeIcon.setImageResource(R.drawable.ic_eye);
                eyeIcon.setContentDescription("Show Password");

            } else {

                // Show password
                passwordField.setInputType(
                        InputType.TYPE_CLASS_TEXT
                                | InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
                );

                eyeIcon.setImageResource(R.drawable.ic_eye);
                eyeIcon.setContentDescription("Hide Password");
            }

            // Keep cursor in its previous position
            passwordField.setSelection(
                    Math.max(0, Math.min(selection,
                            passwordField.getText().length()))
            );

            passwordField.requestFocus();
        });
    }

    // ======================================================
    // REGISTER EMPLOYEE
    // ======================================================

    private void registerEmployee() {

        String employeeName =
                etEmployeeName.getText().toString().trim();

        String employeeId =
                etEmployeeId.getText().toString().trim().toUpperCase();

        String email =
                etEmail.getText().toString().trim().toLowerCase();

        String phone =
                etPhone.getText().toString().trim();

        String password =
                etPassword.getText().toString();

        String confirmPassword =
                etConfirmPassword.getText().toString();

        // Employee name validation
        if (TextUtils.isEmpty(employeeName)) {
            etEmployeeName.setError("Enter employee name");
            etEmployeeName.requestFocus();
            return;
        }

        // Employee ID validation
        if (TextUtils.isEmpty(employeeId)) {
            etEmployeeId.setError("Enter employee ID");
            etEmployeeId.requestFocus();
            return;
        }

        if (!employeeId.startsWith("AFI-")) {
            etEmployeeId.setError("Employee ID must start with AFI-");
            etEmployeeId.requestFocus();
            return;
        }

        if (employeeId.length() <= 4) {
            etEmployeeId.setError("Enter a valid ID, e.g. AFI-001");
            etEmployeeId.requestFocus();
            return;
        }

        // Email validation
        if (TextUtils.isEmpty(email)) {
            etEmail.setError("Enter professional email");
            etEmail.requestFocus();
            return;
        }

        if (!android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            etEmail.setError("Enter a valid email address");
            etEmail.requestFocus();
            return;
        }

        if (!email.endsWith("@arshithgroup.com")) {
            etEmail.setError("Use your @arshithgroup.com email");
            etEmail.requestFocus();
            return;
        }

        // Phone validation
        if (TextUtils.isEmpty(phone)) {
            etPhone.setError("Enter phone number");
            etPhone.requestFocus();
            return;
        }

        if (!phone.matches("\\d{10}")) {
            etPhone.setError("Enter a valid 10-digit phone number");
            etPhone.requestFocus();
            return;
        }

        // Password validation
        if (TextUtils.isEmpty(password)) {
            etPassword.setError("Enter password");
            etPassword.requestFocus();
            return;
        }

        if (password.length() < 6) {
            etPassword.setError(
                    "Password must contain at least 6 characters"
            );
            etPassword.requestFocus();
            return;
        }

        // Confirm password
        if (TextUtils.isEmpty(confirmPassword)) {
            etConfirmPassword.setError("Confirm your password");
            etConfirmPassword.requestFocus();
            return;
        }

        if (!password.equals(confirmPassword)) {
            etConfirmPassword.setError("Passwords do not match");
            etConfirmPassword.requestFocus();
            return;
        }

        // Disable register button
        btnRegister.setEnabled(false);
        btnRegister.setText("Creating Account...");

        // Create Firebase Auth account
        firebaseAuth.createUserWithEmailAndPassword(email, password)
                .addOnSuccessListener(authResult -> {

                    FirebaseUser user = firebaseAuth.getCurrentUser();

                    if (user == null) {
                        showError("Account could not be created.");
                        return;
                    }

                    UserProfileChangeRequest profileUpdates =
                            new UserProfileChangeRequest.Builder()
                                    .setDisplayName(employeeName)
                                    .build();

                    user.updateProfile(profileUpdates)
                            .addOnSuccessListener(unused ->
                                    saveEmployee(
                                            user,
                                            employeeName,
                                            employeeId,
                                            email,
                                            phone
                                    )
                            )
                            .addOnFailureListener(e ->
                                    showError("Name save failed: "
                                            + e.getMessage())
                            );

                })
                .addOnFailureListener(e ->
                        showError("Registration failed: "
                                + e.getMessage())
                );
    }

    // ======================================================
    // SAVE EMPLOYEE TO FIRESTORE
    // ======================================================

    private void saveEmployee(
            FirebaseUser user,
            String employeeName,
            String employeeId,
            String email,
            String phone) {

        Map<String, Object> employee = new HashMap<>();

        employee.put("uid", user.getUid());
        employee.put("employeeId", employeeId);
        employee.put("name", employeeName);
        employee.put("email", email);
        employee.put("phone", phone);
        employee.put("role", "Employee");

        // Wait for admin approval
        employee.put("status", "pending");

        // Approval tracking
        employee.put("reviewedAt", null);
        employee.put("reviewedBy", null);

        // Account creation time
        employee.put("createdAt", FieldValue.serverTimestamp());

        firestore.collection("employees")
                .document(user.getUid())
                .set(employee)
                .addOnSuccessListener(unused -> {
                    // Also create users document for website auth & shared user registry
                    Map<String, Object> userData = new HashMap<>();
                    userData.put("uid", user.getUid());
                    userData.put("email", email.toLowerCase().trim());
                    userData.put("full_name", employeeName);
                    userData.put("role", "EMPLOYEE");
                    userData.put("approval_status", "PENDING");
                    userData.put("is_active", false);
                    userData.put("status", "Pending");
                    userData.put("employee_id", employeeId);
                    userData.put("phone", phone);
                    userData.put("created_at", FieldValue.serverTimestamp());
                    firestore.collection("users").document(user.getUid()).set(userData);

                    // Also create registration_requests document for admin portal
                    Map<String, Object> reqData = new HashMap<>();
                    reqData.put("employee_id", employeeId);
                    reqData.put("name", employeeName);
                    reqData.put("email", email.toLowerCase().trim());
                    reqData.put("phone", phone);
                    reqData.put("status", "Pending");
                    reqData.put("created_at", FieldValue.serverTimestamp());
                    firestore.collection("registration_requests").document(user.getUid()).set(reqData);

                    Toast.makeText(
                            RegisterActivity.this,
                            "Registration submitted. Waiting for admin approval.",
                            Toast.LENGTH_LONG
                    ).show();

                    // Sign out after registration
                    firebaseAuth.signOut();

                    // Go to Login screen
                    Intent intent = new Intent(
                            RegisterActivity.this,
                            MainActivity.class
                    );

                    intent.setFlags(
                            Intent.FLAG_ACTIVITY_NEW_TASK
                                    | Intent.FLAG_ACTIVITY_CLEAR_TASK
                    );

                    startActivity(intent);
                    finish();

                })
                .addOnFailureListener(e ->
                        showError("Employee created, but Firestore failed: "
                                + e.getMessage())
                );
    }

    // ======================================================
    // SHOW ERROR
    // ======================================================

    private void showError(String message) {

        btnRegister.setEnabled(true);
        btnRegister.setText("Register");

        Toast.makeText(
                RegisterActivity.this,
                message,
                Toast.LENGTH_LONG
        ).show();
    }
}
