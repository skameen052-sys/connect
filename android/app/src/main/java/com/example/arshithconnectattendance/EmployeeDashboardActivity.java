package com.example.arshithconnectattendance;

import android.Manifest;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.location.Location;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.text.InputType;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.FileProvider;
import androidx.drawerlayout.widget.DrawerLayout;

import com.google.android.gms.location.FusedLocationProviderClient;
import com.google.android.gms.location.LocationServices;

import com.google.android.material.navigation.NavigationView;

import com.google.firebase.Timestamp;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import com.google.firebase.firestore.DocumentSnapshot;
import com.google.firebase.firestore.FirebaseFirestore;
import com.google.firebase.storage.FirebaseStorage;
import com.google.firebase.storage.StorageMetadata;
import com.google.firebase.storage.StorageReference;

import java.io.File;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;


public class EmployeeDashboardActivity extends AppCompatActivity {

    // ============================================================
    // PERMISSION REQUEST CODES
    // ============================================================

    private static final int LOCATION_PERMISSION_REQUEST_CODE = 1001;
    private static final int CAMERA_REQUEST_CODE = 1002;
    private static final int CAMERA_PERMISSION_REQUEST_CODE = 1003;


    // ============================================================
    // OFFICE LOCATION
    // ============================================================

    private static final double OFFICE_LATITUDE = 12.9104417;
    private static final double OFFICE_LONGITUDE = 77.6442435;
    private static final float OFFICE_RADIUS_METERS = 100f;


    // ============================================================
    // OFFICE START TIME
    // 9:30 AM
    // ============================================================

    private String officeStartTime = null;
    private String officeEndTime = null;
    private int gracePeriodMinutes = 15;
    private boolean officeTimingsLoaded = false;
    private boolean officeTimingsLoading = false;
    private boolean checkInWaitingForTimings = false;


    // ============================================================
    // FIREBASE
    // ============================================================

    private FirebaseAuth auth;
    private FirebaseFirestore firestore;
    private FirebaseStorage storage;
    private FirebaseUser currentUser;

    private FusedLocationProviderClient fusedLocationClient;


    // ============================================================
    // DRAWER
    // ============================================================

    private DrawerLayout drawerLayout;
    private NavigationView navigationView;


    // ============================================================
    // CAMERA
    // ============================================================

    private Uri checkInPhotoUri;
    private File checkInPhotoFile;


    // ============================================================
    // HEADER
    // ============================================================

    private TextView tvWelcome;
    private TextView tvRole;
    private TextView tvCurrentDate;
    private TextView tvCurrentTime;


    // ============================================================
    // TODAY ATTENDANCE
    // ============================================================

    private TextView tvTodayStatus;
    private TextView tvCheckIn;
    private TextView tvCheckOut;
    private TextView tvWorkingDuration;
    private TextView tvWorkMode;

    private Button btnCheckIn;
    private Button btnCheckOut;
    private Button btnLeave;
    private Button btnHistory;


    // ============================================================
    // QUICK ACTIONS
    // ============================================================

    private Button btnAnnouncements;
    private Button btnMeetings;
    private Button btnWorkAssignments;


    // ============================================================
    // LOGOUT
    // ============================================================

    private Button btnLogout;


    // ============================================================
    // MONTHLY SUMMARY
    // ============================================================

    private TextView tvWorkingDays;
    private TextView tvPresentDays;
    private TextView tvAbsentDays;
    private TextView tvAttendancePercentage;


    // ============================================================
    // CLOCK
    // ============================================================

    private Handler clockHandler;
    private Runnable clockRunnable;


    // ============================================================
    // WORK MODE
    // ============================================================

    private String selectedWorkMode = "WFO";


    // ============================================================
    // PREVENT DUPLICATE INITIAL LOAD
    // ============================================================

    private boolean firstResume = true;




    // ============================================================
    // ON CREATE
    // ============================================================

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        try {
            setContentView(R.layout.employee_dashboard);

            auth = FirebaseAuth.getInstance();
            firestore = FirebaseFirestore.getInstance();
            storage = FirebaseStorage.getInstance();
            currentUser = auth.getCurrentUser();

            if (currentUser == null) {
                Toast.makeText(this, "Session expired. Please log in again.", Toast.LENGTH_SHORT).show();
                startActivity(new Intent(EmployeeDashboardActivity.this, MainActivity.class));
                finish();
                return;
            }

            fusedLocationClient =
                    LocationServices.getFusedLocationProviderClient(this);

            initializeViews();
            setupNavigationDrawer();
            setupClickListeners();

            loadEmployeeInformation();
            loadTodayAttendance();
            loadThisMonthSummary();
            loadOfficeTimings();
            startClock();
        } catch (Exception e) {
            android.util.Log.e("EmployeeDashboard", "Error during dashboard onCreate", e);
            Toast.makeText(this, "Could not initialize dashboard. Please try again.", Toast.LENGTH_LONG).show();
        }
    }


    // ============================================================
    // INITIALIZE VIEWS
    // ============================================================

    private void initializeViews() {

        // ========================================================
        // DRAWER
        // ========================================================

        drawerLayout =
                findViewById(R.id.drawerLayout);

        navigationView =
                findViewById(R.id.navigationView);


        // ========================================================
        // HEADER
        // ========================================================

        tvWelcome =
                findViewById(R.id.tvWelcome);

        tvRole =
                findViewById(R.id.tvRole);

        tvCurrentDate =
                findViewById(R.id.tvCurrentDate);

        tvCurrentTime =
                findViewById(R.id.tvCurrentTime);


        // ========================================================
        // TODAY ATTENDANCE
        // ========================================================

        tvTodayStatus =
                findViewById(R.id.tvTodayStatus);

        tvCheckIn =
                findViewById(R.id.tvCheckIn);

        tvCheckOut =
                findViewById(R.id.tvCheckOut);

        tvWorkingDuration =
                findViewById(R.id.tvWorkingDuration);

        tvWorkMode =
                findViewById(R.id.tvWorkMode);


        // ========================================================
        // BUTTONS
        // ========================================================

        btnCheckIn =
                findViewById(R.id.btnCheckIn);

        btnCheckOut =
                findViewById(R.id.btnCheckOut);

        btnLeave =
                findViewById(R.id.btnLeave);

        btnAnnouncements =
                findViewById(R.id.btnAnnouncements);

        btnMeetings =
                findViewById(R.id.btnMeetings);

        btnWorkAssignments =
                findViewById(R.id.btnWorkAssignments);

        btnLogout =
                findViewById(R.id.btnLogout);


        // ========================================================
        // MONTHLY SUMMARY
        // ========================================================

        tvWorkingDays =
                findViewById(R.id.tvWorkingDays);

        tvPresentDays =
                findViewById(R.id.tvPresentDays);

        tvAbsentDays =
                findViewById(R.id.tvAbsentDays);

        tvAttendancePercentage =
                findViewById(R.id.tvAttendancePercentage);


        // ========================================================
        // HISTORY
        // ========================================================

        btnHistory =
                findViewById(R.id.btnHistory);
    }


    // ============================================================
    // NAVIGATION DRAWER
    // ============================================================

    private void setupNavigationDrawer() {

        // ========================================================
        // MENU BUTTON
        // ========================================================

        View btnMenu =
                findViewById(R.id.btnMenu);


        if (btnMenu != null) {

            btnMenu.setOnClickListener(v -> {

                if (drawerLayout != null) {

                    drawerLayout.openDrawer(
                            androidx.core.view.GravityCompat.START
                    );
                }
            });
        }


        // ========================================================
        // NAVIGATION MENU CLICK
        // ========================================================

        if (navigationView != null) {

            navigationView.setNavigationItemSelectedListener(
                    menuItem -> {

                        String title =
                                menuItem.getTitle()
                                        .toString()
                                        .trim();


                        // =================================================
                        // ANNOUNCEMENTS
                        // =================================================

                        if (title.equalsIgnoreCase(
                                "Announcements")) {

                            openAnnouncements();

                        }


                        // =================================================
                        // MEETINGS
                        // =================================================

                        else if (title.equalsIgnoreCase(
                                "Meetings")) {

                            openMeetings();

                        }


                        // =================================================
                        // WORK ASSIGNMENTS
                        // =================================================

                        else if (title.equalsIgnoreCase(
                                "Work Assignments")) {

                            openWorkAssignments();

                        }


                        // =================================================
                        // LEAVE MANAGEMENT
                        // =================================================

                        else if (title.equalsIgnoreCase(
                                "Leave Management")) {

                            openLeaveManagement();

                        }


                        // =================================================
                        // PROFILE
                        // =================================================

                        else if (title.equalsIgnoreCase(
                                "Profile")) {

                            openProfile();

                        }


                        // =================================================
                        // WORK UPDATE
                        // =================================================

                        else if (title.equalsIgnoreCase(
                                "Work Update")) {

                            openWorkUpdate();

                        }


                        // =================================================
                        // CLOSE DRAWER
                        // =================================================

                        if (drawerLayout != null) {

                            drawerLayout.closeDrawer(
                                    androidx.core.view.GravityCompat.START
                            );
                        }


                        return true;
                    }
            );
        }
    }





    private void loadOfficeTimings() {

        if (officeTimingsLoading) {
            return;
        }

        officeTimingsLoading = true;
        officeTimingsLoaded = false;

        String today = new SimpleDateFormat(
                "yyyy-MM-dd",
                Locale.getDefault()
        ).format(new Date());

        // Check today's special timings first.
        firestore.collection("specialOfficeTimings")
                .document(today)
                .get()
                .addOnSuccessListener(specialDocument -> {

                    if (specialDocument.exists()) {

                        boolean valid =
                                applyOfficeTimingDocument(specialDocument);

                        officeTimingsLoading = false;

                        if (valid) {
                            resumePendingCheckInIfNeeded();
                        } else {
                            checkInWaitingForTimings = false;

                            Toast.makeText(
                                    this,
                                    "Today's special office timings are invalid. Please contact the admin.",
                                    Toast.LENGTH_LONG
                            ).show();
                        }

                    } else {

                        // No special timings today: use regular admin settings.
                        loadRegularOfficeTimings();
                    }
                })
                .addOnFailureListener(e -> {

                    officeTimingsLoading = false;
                    officeTimingsLoaded = false;
                    checkInWaitingForTimings = false;

                    Toast.makeText(
                            this,
                            "Unable to check today's special timings. Check your connection.",
                            Toast.LENGTH_LONG
                    ).show();
                });
    }


    private void loadRegularOfficeTimings() {

        firestore.collection("settings")
                .document("officeTimings")
                .get()
                .addOnSuccessListener(document -> {

                    if (!document.exists()) {

                        officeTimingsLoading = false;
                        officeTimingsLoaded = false;
                        checkInWaitingForTimings = false;

                        Toast.makeText(
                                this,
                                "Office timings have not been configured by the admin.",
                                Toast.LENGTH_LONG
                        ).show();

                        return;
                    }

                    boolean valid =
                            applyOfficeTimingDocument(document);

                    officeTimingsLoading = false;

                    if (valid) {
                        resumePendingCheckInIfNeeded();
                    } else {
                        checkInWaitingForTimings = false;

                        Toast.makeText(
                                this,
                                "Regular office timing settings are incomplete or invalid.",
                                Toast.LENGTH_LONG
                        ).show();
                    }
                })
                .addOnFailureListener(e -> {

                    officeTimingsLoading = false;
                    officeTimingsLoaded = false;
                    checkInWaitingForTimings = false;

                    Toast.makeText(
                            this,
                            "Unable to load regular office timings. Check your connection.",
                            Toast.LENGTH_LONG
                    ).show();
                });
    }


    private boolean applyOfficeTimingDocument(
            DocumentSnapshot document
    ) {

        String start =
                document.getString("officeStartTime");

        String end =
                document.getString("officeEndTime");

        Long grace =
                document.getLong("gracePeriodMinutes");

        if (start == null || end == null || grace == null) {
            officeTimingsLoaded = false;
            return false;
        }

        try {

            SimpleDateFormat format =
                    new SimpleDateFormat("HH:mm", Locale.US);

            format.setLenient(false);

            Date startDate = format.parse(start);
            Date endDate = format.parse(end);

            if (startDate == null
                    || endDate == null
                    || !start.matches("\\d{2}:\\d{2}")
                    || !end.matches("\\d{2}:\\d{2}")
                    || !startDate.before(endDate)
                    || grace < 0
                    || grace > 180) {

                officeTimingsLoaded = false;
                return false;
            }

            officeStartTime = start;
            officeEndTime = end;
            gracePeriodMinutes = grace.intValue();

            officeTimingsLoaded = true;

            return true;

        } catch (Exception e) {

            officeTimingsLoaded = false;
            return false;
        }
    }


    private void resumePendingCheckInIfNeeded() {

        if (officeTimingsLoaded && checkInWaitingForTimings) {

            checkInWaitingForTimings = false;

            // Continue check-in after Firebase returns the timings.
            checkLateAndCheckIn();
        }
    }



    // ============================================================
    // OPEN ANNOUNCEMENTS
    // ============================================================

    private void openAnnouncements() {
        try {
            Intent intent =
                    new Intent(
                            EmployeeDashboardActivity.this,
                            EmployeeAnnouncementsActivity.class
                    );

            startActivity(intent);
        } catch (Exception e) {
            android.util.Log.e("EmployeeDashboard", "Could not start EmployeeAnnouncementsActivity", e);
            Toast.makeText(this, "Announcements screen is temporarily unavailable.", Toast.LENGTH_SHORT).show();
        }
    }


    // ============================================================
    // OPEN MEETINGS
    // ============================================================

    private void openMeetings() {

        Intent intent =
                new Intent(
                        EmployeeDashboardActivity.this,
                        EmployeeMeetingManagementActivity.class
                );

        startActivity(intent);
    }


    // ============================================================
    // OPEN WORK ASSIGNMENTS
    // ============================================================

    private void openWorkAssignments() {

        Intent intent =
                new Intent(
                        EmployeeDashboardActivity.this,
                        EmployeeWorkAssignmentsActivity.class
                );

        startActivity(intent);
    }


    // ============================================================
    // OPEN LEAVE MANAGEMENT
    // ============================================================

    private void openLeaveManagement() {

        Intent intent =
                new Intent(
                        EmployeeDashboardActivity.this,
                        LeaveManagementActivity.class
                );

        startActivity(intent);
    }


    // ============================================================
    // OPEN WORK UPDATE
    // ============================================================

    private void openWorkUpdate() {

        try {

            Intent intent =
                    new Intent(
                            EmployeeDashboardActivity.this,
                            EmployeeWorkUpdateActivity.class
                    );

            startActivity(intent);

        } catch (Exception e) {

            Toast.makeText(
                    this,
                    "Work Update screen is not available.",
                    Toast.LENGTH_LONG
            ).show();
        }
    }


    // ============================================================
    // OPEN PROFILE
    // ============================================================

    private void openProfile() {

        try {

            Intent intent =
                    new Intent(
                            EmployeeDashboardActivity.this,
                            EmployeeProfileActivity.class
                    );

            startActivity(intent);

        } catch (Exception e) {

            Toast.makeText(
                    this,
                    "Profile screen is not available.",
                    Toast.LENGTH_LONG
            ).show();
        }
    }


    // ============================================================
    // DASHBOARD CLICK LISTENERS
    // ============================================================

    private void setupClickListeners() {

        // ========================================================
        // CHECK IN
        // ========================================================

        if (btnCheckIn != null) {

            btnCheckIn.setOnClickListener(v ->
                    showWorkModeDialog()
            );
        }


        // ========================================================
        // CHECK OUT
        // ========================================================

        if (btnCheckOut != null) {

            btnCheckOut.setOnClickListener(v ->
                    checkOut()
            );
        }


        // ========================================================
        // LEAVE
        // ========================================================

        if (btnLeave != null) {

            btnLeave.setOnClickListener(v ->
                    openLeaveManagement()
            );
        }


        // ========================================================
        // WORK ASSIGNMENTS
        // ========================================================

        if (btnWorkAssignments != null) {

            btnWorkAssignments.setOnClickListener(v ->
                    openWorkAssignments()
            );
        }


        // ========================================================
        // ANNOUNCEMENTS
        // ========================================================

        if (btnAnnouncements != null) {

            btnAnnouncements.setOnClickListener(v ->
                    openAnnouncements()
            );
        }


        // ========================================================
        // MEETINGS
        // ========================================================

        if (btnMeetings != null) {

            btnMeetings.setOnClickListener(v ->
                    openMeetings()
            );
        }


        // ========================================================
        // LOGOUT
        // ========================================================

        if (btnLogout != null) {

            btnLogout.setOnClickListener(v -> {

                auth.signOut();


                getSharedPreferences(
                        "ArshithConnectPrefs",
                        MODE_PRIVATE
                )
                        .edit()
                        .remove("loginType")
                        .apply();


                Intent intent =
                        new Intent(
                                EmployeeDashboardActivity.this,
                                MainActivity.class
                        );


                intent.setFlags(
                        Intent.FLAG_ACTIVITY_NEW_TASK |
                                Intent.FLAG_ACTIVITY_CLEAR_TASK
                );


                startActivity(intent);

                finish();
            });
        }
    }


    // ============================================================
    // EMPLOYEE INFORMATION
    // ============================================================

    private void loadEmployeeInformation() {

        if (currentUser == null) {
            return;
        }


        String employeeName =
                currentUser.getDisplayName();


        if (employeeName != null &&
                !employeeName.trim().isEmpty()) {

            employeeName =
                    employeeName.trim();

        } else {

            employeeName =
                    "Employee";
        }


        if (tvWelcome != null) {

            tvWelcome.setText(
                    "Welcome,\n" + employeeName
            );
        }


        if (tvRole != null) {

            tvRole.setText("Employee");
        }
    }


    // ============================================================
    // CLOCK
    // ============================================================

    private void startClock() {

        clockHandler =
                new Handler(
                        Looper.getMainLooper()
                );


        clockRunnable =
                new Runnable() {

                    @Override
                    public void run() {

                        Calendar calendar =
                                Calendar.getInstance();


                        SimpleDateFormat dateFormat =
                                new SimpleDateFormat(
                                        "EEEE, dd MMMM yyyy",
                                        Locale.getDefault()
                                );


                        SimpleDateFormat timeFormat =
                                new SimpleDateFormat(
                                        "hh:mm:ss a",
                                        Locale.getDefault()
                                );


                        if (tvCurrentDate != null) {

                            tvCurrentDate.setText(
                                    dateFormat.format(
                                            calendar.getTime()
                                    )
                            );
                        }


                        if (tvCurrentTime != null) {

                            tvCurrentTime.setText(
                                    timeFormat.format(
                                            calendar.getTime()
                                    )
                            );
                        }


                        if (clockHandler != null) {

                            clockHandler.postDelayed(
                                    this,
                                    1000
                            );
                        }
                    }
                };


        clockHandler.post(clockRunnable);
    }


    // ============================================================
    // WORK MODE DIALOG
    // ============================================================

    private void showWorkModeDialog() {

        RadioGroup radioGroup =
                new RadioGroup(this);

        radioGroup.setOrientation(
                RadioGroup.VERTICAL
        );


        RadioButton wfo =
                new RadioButton(this);

        wfo.setText(
                "Work From Office (WFO)"
        );

        wfo.setId(
                View.generateViewId()
        );


        RadioButton wfh =
                new RadioButton(this);

        wfh.setText(
                "Work From Home (WFH)"
        );

        wfh.setId(
                View.generateViewId()
        );


        radioGroup.addView(wfo);
        radioGroup.addView(wfh);

        wfo.setChecked(true);


        AlertDialog dialog =
                new AlertDialog.Builder(this)
                        .setTitle("Select Work Mode")
                        .setView(radioGroup)
                        .setPositiveButton(
                                "Continue",
                                null
                        )
                        .setNegativeButton(
                                "Cancel",
                                null
                        )
                        .create();


        dialog.setOnShowListener(d -> {

            dialog.getButton(
                    AlertDialog.BUTTON_POSITIVE
            ).setOnClickListener(v -> {

                if (wfo.isChecked()) {

                    selectedWorkMode = "WFO";

                } else {

                    selectedWorkMode = "WFH";
                }


                dialog.dismiss();

                checkLocationAndCheckIn();
            });
        });


        dialog.show();
    }


    // ============================================================
    // CHECK LOCATION AND CHECK IN
    // ============================================================

    private void checkLocationAndCheckIn() {

        if ("WFH".equals(selectedWorkMode)) {

            checkLateAndCheckIn();

            return;
        }


        boolean fineLocationGranted =
                ActivityCompat.checkSelfPermission(
                        this,
                        Manifest.permission.ACCESS_FINE_LOCATION
                ) == PackageManager.PERMISSION_GRANTED;


        boolean coarseLocationGranted =
                ActivityCompat.checkSelfPermission(
                        this,
                        Manifest.permission.ACCESS_COARSE_LOCATION
                ) == PackageManager.PERMISSION_GRANTED;


        if (!fineLocationGranted &&
                !coarseLocationGranted) {

            ActivityCompat.requestPermissions(
                    this,
                    new String[]{
                            Manifest.permission.ACCESS_FINE_LOCATION,
                            Manifest.permission.ACCESS_COARSE_LOCATION
                    },
                    LOCATION_PERMISSION_REQUEST_CODE
            );

            return;
        }


        fusedLocationClient
                .getLastLocation()
                .addOnSuccessListener(location -> {

                    if (location == null) {

                        Toast.makeText(
                                this,
                                "Unable to get your location. Please turn on GPS.",
                                Toast.LENGTH_LONG
                        ).show();

                        return;
                    }


                    Location officeLocation =
                            new Location("office");


                    officeLocation.setLatitude(
                            OFFICE_LATITUDE
                    );


                    officeLocation.setLongitude(
                            OFFICE_LONGITUDE
                    );


                    float distance =
                            location.distanceTo(
                                    officeLocation
                            );


                    if (distance <=
                            OFFICE_RADIUS_METERS) {

                        openCameraForCheckIn();

                    } else {

                        Toast.makeText(
                                this,
                                "You are outside the office location.",
                                Toast.LENGTH_LONG
                        ).show();
                    }

                })
                .addOnFailureListener(e -> {

                    Toast.makeText(
                            this,
                            "Unable to get location: "
                                    + e.getMessage(),
                            Toast.LENGTH_LONG
                    ).show();
                });
    }


    // ============================================================
    // OPEN CAMERA
    // ============================================================

    private void openCameraForCheckIn() {

        if (currentUser == null) {
            return;
        }


        if (ActivityCompat.checkSelfPermission(
                this,
                Manifest.permission.CAMERA
        ) != PackageManager.PERMISSION_GRANTED) {

            ActivityCompat.requestPermissions(
                    this,
                    new String[]{
                            Manifest.permission.CAMERA
                    },
                    CAMERA_PERMISSION_REQUEST_CODE
            );

            return;
        }


        try {

            File picturesDirectory =
                    new File(
                            getExternalFilesDir(
                                    Environment.DIRECTORY_PICTURES
                            ),
                            "attendance"
                    );


            if (!picturesDirectory.exists()) {

                boolean created =
                        picturesDirectory.mkdirs();


                if (!created &&
                        !picturesDirectory.exists()) {

                    Toast.makeText(
                            this,
                            "Unable to create photo storage.",
                            Toast.LENGTH_LONG
                    ).show();

                    return;
                }
            }


            String fileName =
                    "checkin_"
                            + currentUser.getUid()
                            + "_"
                            + System.currentTimeMillis()
                            + ".jpg";


            checkInPhotoFile =
                    new File(
                            picturesDirectory,
                            fileName
                    );


            checkInPhotoUri =
                    FileProvider.getUriForFile(
                            this,
                            getPackageName()
                                    + ".fileprovider",
                            checkInPhotoFile
                    );


            Intent cameraIntent =
                    new Intent(
                            MediaStore.ACTION_IMAGE_CAPTURE
                    );


            cameraIntent.putExtra(
                    MediaStore.EXTRA_OUTPUT,
                    checkInPhotoUri
            );


            cameraIntent.addFlags(
                    Intent.FLAG_GRANT_READ_URI_PERMISSION |
                            Intent.FLAG_GRANT_WRITE_URI_PERMISSION |
                            Intent.FLAG_ACTIVITY_CLEAR_TOP
            );


            cameraIntent.setClipData(
                    ClipData.newRawUri(
                            "CheckInPhoto",
                            checkInPhotoUri
                    )
            );


            try {

                startActivityForResult(
                        cameraIntent,
                        CAMERA_REQUEST_CODE
                );

            } catch (ActivityNotFoundException e) {

                Toast.makeText(
                        this,
                        "No camera application is installed on this phone.",
                        Toast.LENGTH_LONG
                ).show();


                deleteTemporaryPhoto();
            }

        } catch (Exception e) {

            Toast.makeText(
                    this,
                    "Unable to open camera: "
                            + e.getMessage(),
                    Toast.LENGTH_LONG
            ).show();


            deleteTemporaryPhoto();
        }
    }


    // ============================================================
    // CAMERA RESULT
    // ============================================================

    @Override
    protected void onActivityResult(
            int requestCode,
            int resultCode,
            Intent data
    ) {

        super.onActivityResult(
                requestCode,
                resultCode,
                data
        );


        if (requestCode != CAMERA_REQUEST_CODE) {
            return;
        }


        if (resultCode != Activity.RESULT_OK) {

            deleteTemporaryPhoto();


            Toast.makeText(
                    this,
                    "Check-in photo is required for WFO.",
                    Toast.LENGTH_LONG
            ).show();


            return;
        }


        if (checkInPhotoFile == null ||
                checkInPhotoUri == null ||
                !checkInPhotoFile.exists() ||
                checkInPhotoFile.length() == 0) {

            deleteTemporaryPhoto();


            Toast.makeText(
                    this,
                    "Photo was not captured. Please try again.",
                    Toast.LENGTH_LONG
            ).show();


            return;
        }


        Toast.makeText(
                this,
                "Photo captured successfully.",
                Toast.LENGTH_SHORT
        ).show();


        checkLateAndCheckIn();
    }


    // ============================================================
    // DELETE TEMPORARY PHOTO
    // ============================================================

    private void deleteTemporaryPhoto() {

        if (checkInPhotoFile != null &&
                checkInPhotoFile.exists()) {

            try {

                checkInPhotoFile.delete();

            } catch (Exception ignored) {
            }
        }


        checkInPhotoFile = null;
        checkInPhotoUri = null;
    }



    private void checkLateAndCheckIn() {

        if (!officeTimingsLoaded || officeStartTime == null) {

            checkInWaitingForTimings = true;

            Toast.makeText(
                    this,
                    "Loading today's office timings. Please wait.",
                    Toast.LENGTH_SHORT
            ).show();

            loadOfficeTimings();
            return;
        }

        try {

            SimpleDateFormat format =
                    new SimpleDateFormat("HH:mm", Locale.US);

            format.setLenient(false);

            Date parsedStart = format.parse(officeStartTime);

            if (parsedStart == null) {
                throw new IllegalArgumentException("Invalid start time");
            }

            Calendar startCalendar = Calendar.getInstance();
            Calendar parsedCalendar = Calendar.getInstance();

            parsedCalendar.setTime(parsedStart);

            startCalendar.set(
                    Calendar.HOUR_OF_DAY,
                    parsedCalendar.get(Calendar.HOUR_OF_DAY)
            );

            startCalendar.set(
                    Calendar.MINUTE,
                    parsedCalendar.get(Calendar.MINUTE)
            );

            startCalendar.set(Calendar.SECOND, 0);
            startCalendar.set(Calendar.MILLISECOND, 0);

            Calendar deadline = (Calendar) startCalendar.clone();

            deadline.add(
                    Calendar.MINUTE,
                    gracePeriodMinutes
            );

            Calendar now = Calendar.getInstance();

            boolean isLate = now.after(deadline);

            if (isLate) {
                showLateReasonDialog();
            } else {
                saveCheckIn(false, "");
            }

        } catch (Exception e) {

            Toast.makeText(
                    this,
                    "Unable to validate check-in time.",
                    Toast.LENGTH_LONG
            ).show();
        }
    }




    // ============================================================
    // LATE REASON
    // ============================================================

    private void showLateReasonDialog() {

        EditText input =
                new EditText(this);


        input.setHint(
                "Enter late login reason"
        );


        input.setInputType(
                InputType.TYPE_CLASS_TEXT |
                        InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
        );


        int padding = 40;


        input.setPadding(
                padding,
                padding,
                padding,
                padding
        );


        AlertDialog dialog =
                new AlertDialog.Builder(this)
                        .setTitle("Late Login")
                        .setMessage(
                                "You are checking in after the allowed office start time. Please provide a reason."
                        )
                        .setView(input)
                        .setPositiveButton(
                                "Submit",
                                null
                        )
                        .setNegativeButton(
                                "Cancel",
                                null
                        )
                        .create();


        dialog.setOnShowListener(d -> {

            dialog.getButton(
                    AlertDialog.BUTTON_POSITIVE
            ).setOnClickListener(v -> {

                String reason =
                        input.getText()
                                .toString()
                                .trim();


                if (reason.isEmpty()) {

                    input.setError(
                            "Please enter a reason"
                    );

                    return;
                }


                dialog.dismiss();


                saveCheckIn(
                        true,
                        reason
                );
            });
        });


        dialog.show();
    }


    // ============================================================
    // SAVE CHECK IN
    // ============================================================

    private void saveCheckIn(
            boolean lateLogin,
            String lateReason
    ) {

        if (currentUser == null) {
            return;
        }


        if ("WFO".equals(selectedWorkMode) &&
                (
                        checkInPhotoUri == null ||
                                checkInPhotoFile == null ||
                                !checkInPhotoFile.exists()
                )) {

            Toast.makeText(
                    this,
                    "Office photo is required for WFO check-in.",
                    Toast.LENGTH_LONG
            ).show();

            return;
        }


        String uid =
                currentUser.getUid();


        Date now =
                new Date();


        String date =
                new SimpleDateFormat(
                        "yyyy-MM-dd",
                        Locale.getDefault()
                ).format(now);


        firestore
                .collection("attendance")
                .document(uid)
                .collection("records")
                .document(date)
                .get()
                .addOnSuccessListener(document -> {

                    if (document.exists()) {

                        Toast.makeText(
                                this,
                                "You have already checked in today.",
                                Toast.LENGTH_LONG
                        ).show();


                        deleteTemporaryPhoto();

                        loadTodayAttendance();

                        return;
                    }


                    if ("WFO".equals(selectedWorkMode)) {

                        uploadCheckInPhotoAndSaveAttendance(
                                uid,
                                date,
                                lateLogin,
                                lateReason
                        );

                    } else {

                        saveAttendanceRecord(
                                uid,
                                date,
                                lateLogin,
                                lateReason,
                                null
                        );
                    }

                })
                .addOnFailureListener(e -> {

                    Toast.makeText(
                            this,
                            "Unable to check attendance: "
                                    + e.getMessage(),
                            Toast.LENGTH_LONG
                    ).show();
                });
    }


    // ============================================================
    // UPLOAD PHOTO
    // ============================================================

    private void uploadCheckInPhotoAndSaveAttendance(
            String uid,
            String date,
            boolean lateLogin,
            String lateReason
    ) {

        if (checkInPhotoUri == null) {

            Toast.makeText(
                    this,
                    "Office photo is required.",
                    Toast.LENGTH_LONG
            ).show();

            return;
        }


        Toast.makeText(
                this,
                "Uploading office photo...",
                Toast.LENGTH_SHORT
        ).show();


        StorageReference photoReference =
                storage
                        .getReference()
                        .child(
                                "attendancePhotos/"
                                        + uid
                                        + "/"
                                        + date
                                        + ".jpg"
                        );


        StorageMetadata metadata =
                new StorageMetadata.Builder()
                        .setContentType("image/jpeg")
                        .build();


        photoReference
                .putFile(
                        checkInPhotoUri,
                        metadata
                )
                .addOnSuccessListener(
                        uploadTask -> {

                            photoReference
                                    .getDownloadUrl()
                                    .addOnSuccessListener(
                                            downloadUri -> {

                                                saveAttendanceRecord(
                                                        uid,
                                                        date,
                                                        lateLogin,
                                                        lateReason,
                                                        downloadUri.toString()
                                                );
                                            }
                                    )
                                    .addOnFailureListener(e -> {

                                        Toast.makeText(
                                                this,
                                                "Unable to get photo URL: "
                                                        + e.getMessage(),
                                                Toast.LENGTH_LONG
                                        ).show();


                                        deleteTemporaryPhoto();
                                    });

                        }
                )
                .addOnFailureListener(e -> {

                    Toast.makeText(
                            this,
                            "Photo upload failed: "
                                    + e.getMessage(),
                            Toast.LENGTH_LONG
                    ).show();


                    deleteTemporaryPhoto();
                });
    }


    // ============================================================
    // SAVE ATTENDANCE RECORD
    // ============================================================

    private void saveAttendanceRecord(
            String uid,
            String date,
            boolean lateLogin,
            String lateReason,
            String photoUrl
    ) {

        java.util.Map<String, Object> data =
                new java.util.HashMap<>();


        data.put("employeeId", uid);

        data.put(
                "email",
                currentUser.getEmail()
        );

        data.put("date", date);

        data.put(
                "checkIn",
                Timestamp.now()
        );

        data.put(
                "status",
                "Present"
        );

        data.put(
                "workMode",
                selectedWorkMode
        );

        data.put(
                "lateLogin",
                lateLogin
        );

        data.put(
                "lateReason",
                lateReason
        );


        if (photoUrl != null &&
                !photoUrl.trim().isEmpty()) {

            data.put(
                    "checkInPhotoUrl",
                    photoUrl
            );

            data.put(
                    "photoCaptured",
                    true
            );

        } else {

            data.put(
                    "photoCaptured",
                    false
            );
        }


        firestore
                .collection("attendance")
                .document(uid)
                .collection("records")
                .document(date)
                .set(data)
                .addOnSuccessListener(unused -> {

                    Toast.makeText(
                            this,
                            "Check-in successful.",
                            Toast.LENGTH_SHORT
                    ).show();


                    deleteTemporaryPhoto();

                    loadTodayAttendance();

                    loadThisMonthSummary();

                })
                .addOnFailureListener(e -> {

                    Toast.makeText(
                            this,
                            "Check-in failed: "
                                    + e.getMessage(),
                            Toast.LENGTH_LONG
                    ).show();
                });
    }


    // ============================================================
    // CHECK OUT
    // ============================================================

    private void checkOut() {

        if (currentUser == null) {
            return;
        }


        String uid =
                currentUser.getUid();


        String date =
                new SimpleDateFormat(
                        "yyyy-MM-dd",
                        Locale.getDefault()
                ).format(new Date());


        firestore
                .collection("attendance")
                .document(uid)
                .collection("records")
                .document(date)
                .get()
                .addOnSuccessListener(document -> {

                    if (!document.exists()) {

                        Toast.makeText(
                                this,
                                "Please check in first.",
                                Toast.LENGTH_LONG
                        ).show();

                        return;
                    }


                    if (document.contains("checkOut")) {

                        Toast.makeText(
                                this,
                                "You have already checked out today.",
                                Toast.LENGTH_LONG
                        ).show();


                        loadTodayAttendance();

                        return;
                    }


                    java.util.Map<String, Object> update =
                            new java.util.HashMap<>();


                    update.put(
                            "checkOut",
                            Timestamp.now()
                    );


                    firestore
                            .collection("attendance")
                            .document(uid)
                            .collection("records")
                            .document(date)
                            .update(update)
                            .addOnSuccessListener(unused -> {

                                Toast.makeText(
                                        this,
                                        "Check-out successful.",
                                        Toast.LENGTH_SHORT
                                ).show();


                                loadTodayAttendance();

                                loadThisMonthSummary();

                            })
                            .addOnFailureListener(e -> {

                                Toast.makeText(
                                        this,
                                        "Check-out failed: "
                                                + e.getMessage(),
                                        Toast.LENGTH_LONG
                                ).show();
                            });

                })
                .addOnFailureListener(e -> {

                    Toast.makeText(
                            this,
                            "Unable to load attendance.",
                            Toast.LENGTH_LONG
                    ).show();
                });
    }


    // ============================================================
    // LOAD TODAY ATTENDANCE
    // ============================================================

    private void loadTodayAttendance() {

        if (currentUser == null) {
            return;
        }


        String uid =
                currentUser.getUid();


        String date =
                new SimpleDateFormat(
                        "yyyy-MM-dd",
                        Locale.getDefault()
                ).format(new Date());


        firestore
                .collection("attendance")
                .document(uid)
                .collection("records")
                .document(date)
                .get()
                .addOnSuccessListener(document -> {

                    if (!document.exists()) {

                        if (tvTodayStatus != null) {
                            tvTodayStatus.setText(
                                    "● Not Checked In"
                            );
                        }

                        if (tvCheckIn != null) {
                            tvCheckIn.setText(
                                    "Check-in: --"
                            );
                        }

                        if (tvCheckOut != null) {
                            tvCheckOut.setText(
                                    "Check-out: --"
                            );
                        }

                        if (tvWorkingDuration != null) {
                            tvWorkingDuration.setText(
                                    "Working Duration: --"
                            );
                        }

                        if (tvWorkMode != null) {
                            tvWorkMode.setText(
                                    "Work Mode: --"
                            );
                        }

                        if (btnCheckIn != null) {
                            btnCheckIn.setEnabled(true);
                        }

                        if (btnCheckOut != null) {
                            btnCheckOut.setEnabled(false);
                        }

                        return;
                    }


                    Timestamp checkIn = null;
                    Timestamp checkOut = null;
                    try {
                        Object cIn = document.get("checkIn");
                        if (cIn instanceof Timestamp) {
                            checkIn = (Timestamp) cIn;
                        }
                    } catch (Exception ignored) {}

                    try {
                        Object cOut = document.get("checkOut");
                        if (cOut instanceof Timestamp) {
                            checkOut = (Timestamp) cOut;
                        }
                    } catch (Exception ignored) {}


                    String workMode =
                            document.getString("workMode");


                    if (tvTodayStatus != null) {

                        if (checkOut != null) {

                            tvTodayStatus.setText(
                                    "● Completed"
                            );

                        } else {

                            tvTodayStatus.setText(
                                    "● Working"
                            );
                        }
                    }


                    if (tvCheckIn != null) {

                        if (checkIn != null) {

                            tvCheckIn.setText(
                                    "Check-in: "
                                            + formatTime(checkIn)
                            );

                        } else {

                            tvCheckIn.setText(
                                    "Check-in: --"
                            );
                        }
                    }


                    if (tvCheckOut != null) {

                        if (checkOut != null) {

                            tvCheckOut.setText(
                                    "Check-out: "
                                            + formatTime(checkOut)
                            );

                        } else {

                            tvCheckOut.setText(
                                    "Check-out: --"
                            );
                        }
                    }


                    if (tvWorkMode != null) {

                        if (workMode != null) {

                            tvWorkMode.setText(
                                    "Work Mode: "
                                            + workMode
                            );

                        } else {

                            tvWorkMode.setText(
                                    "Work Mode: --"
                            );
                        }
                    }


                    if (tvWorkingDuration != null) {

                        if (checkIn != null &&
                                checkOut != null) {

                            tvWorkingDuration.setText(
                                    "Working Duration: "
                                            +
                                            calculateWorkingDuration(
                                                    checkIn,
                                                    checkOut
                                            )
                            );

                        } else {

                            tvWorkingDuration.setText(
                                    "Working Duration: --"
                            );
                        }
                    }


                    if (btnCheckIn != null) {
                        btnCheckIn.setEnabled(false);
                    }


                    if (btnCheckOut != null) {

                        btnCheckOut.setEnabled(
                                checkOut == null
                        );
                    }

                })
                .addOnFailureListener(e -> {

                    Toast.makeText(
                            this,
                            "Unable to load today's attendance: "
                                    + e.getMessage(),
                            Toast.LENGTH_LONG
                    ).show();
                });
    }


    // ============================================================
    // MONTHLY SUMMARY
    // ============================================================

    private void loadThisMonthSummary() {

        if (currentUser == null) {
            return;
        }


        String uid =
                currentUser.getUid();


        firestore
                .collection("employees")
                .document(uid)
                .get()
                .addOnSuccessListener(employeeDocument -> {

                    Date employeeStartDate = null;


                    if (employeeDocument.exists()) {
                        try {
                            Object rawCreated = employeeDocument.get("createdAt");
                            if (rawCreated instanceof Timestamp) {
                                employeeStartDate = ((Timestamp) rawCreated).toDate();
                            } else if (rawCreated instanceof Date) {
                                employeeStartDate = (Date) rawCreated;
                            }
                        } catch (Exception ignored) {}
                    }


                    if (employeeStartDate == null &&
                            currentUser.getMetadata() != null &&
                            currentUser.getMetadata()
                                    .getCreationTimestamp() > 0) {

                        employeeStartDate =
                                new Date(
                                        currentUser
                                                .getMetadata()
                                                .getCreationTimestamp()
                                );
                    }


                    calculateThisMonthSummary(
                            employeeStartDate
                    );

                })
                .addOnFailureListener(e -> {

                    Date employeeStartDate = null;


                    if (currentUser.getMetadata() != null &&
                            currentUser.getMetadata()
                                    .getCreationTimestamp() > 0) {

                        employeeStartDate =
                                new Date(
                                        currentUser
                                                .getMetadata()
                                                .getCreationTimestamp()
                                );
                    }


                    calculateThisMonthSummary(
                            employeeStartDate
                    );
                });
    }


    // ============================================================
    // CALCULATE MONTHLY SUMMARY
    // ============================================================

    private void calculateThisMonthSummary(
            Date employeeStartDate
    ) {

        Calendar today =
                Calendar.getInstance();

        setStartOfDay(today);


        Calendar monthStart =
                Calendar.getInstance();

        monthStart.set(
                Calendar.DAY_OF_MONTH,
                1
        );

        setStartOfDay(monthStart);


        Calendar calculationStartTemp =
                (Calendar) monthStart.clone();


        if (employeeStartDate != null) {

            Calendar employeeStart =
                    Calendar.getInstance();

            employeeStart.setTime(
                    employeeStartDate
            );

            setStartOfDay(employeeStart);


            if (employeeStart.after(
                    calculationStartTemp
            )) {

                calculationStartTemp =
                        employeeStart;
            }
        }


        if (calculationStartTemp.after(today)) {

            updateThisMonthViews(
                    0,
                    0,
                    0,
                    0
            );

            return;
        }


        final Calendar calculationStart =
                (Calendar)
                        calculationStartTemp.clone();


        final Calendar calculationEnd =
                (Calendar)
                        today.clone();


        String startDate =
                formatDate(
                        calculationStart.getTime()
                );


        String endDate =
                formatDate(
                        calculationEnd.getTime()
                );


        firestore
                .collection("holidays")
                .get()
                .addOnSuccessListener(
                        holidaySnapshot -> {

                            Set<String> holidayDates =
                                    new HashSet<>();


                            for (DocumentSnapshot document :
                                    holidaySnapshot.getDocuments()) {

                                String holidayDate =
                                        document.getString(
                                                "date"
                                        );


                                if (holidayDate != null &&
                                        !holidayDate.trim().isEmpty()) {

                                    holidayDates.add(
                                            holidayDate.trim()
                                    );
                                }
                            }


                            loadAttendanceForThisMonth(
                                    startDate,
                                    endDate,
                                    calculationStart,
                                    calculationEnd,
                                    holidayDates
                            );

                        }
                )
                .addOnFailureListener(e -> {

                    loadAttendanceForThisMonth(
                            startDate,
                            endDate,
                            calculationStart,
                            calculationEnd,
                            new HashSet<>()
                    );
                });
    }


    // ============================================================
    // LOAD MONTH ATTENDANCE
    // ============================================================

    private void loadAttendanceForThisMonth(
            String startDate,
            String endDate,
            Calendar calculationStart,
            Calendar calculationEnd,
            Set<String> holidayDates
    ) {

        if (currentUser == null) {
            return;
        }


        String uid =
                currentUser.getUid();


        Set<String> approvedLeaveDates =
                new HashSet<>();


        firestore
                .collection("leaves")
                .document(uid)
                .collection("requests")
                .whereEqualTo(
                        "status",
                        "Approved"
                )
                .get()
                .addOnSuccessListener(
                        leaveSnapshot -> {

                            for (DocumentSnapshot document :
                                    leaveSnapshot.getDocuments()) {

                                addLeaveDates(
                                        document,
                                        approvedLeaveDates,
                                        calculationStart,
                                        calculationEnd
                                );
                            }


                            firestore
                                    .collection("attendance")
                                    .document(uid)
                                    .collection("records")
                                    .whereGreaterThanOrEqualTo(
                                            "date",
                                            startDate
                                    )
                                    .whereLessThanOrEqualTo(
                                            "date",
                                            endDate
                                    )
                                    .get()
                                    .addOnSuccessListener(
                                            attendanceSnapshot -> {

                                                calculateAttendanceSummary(
                                                        attendanceSnapshot,
                                                        calculationStart,
                                                        calculationEnd,
                                                        holidayDates,
                                                        approvedLeaveDates
                                                );

                                            }
                                    )
                                    .addOnFailureListener(e -> {

                                        updateThisMonthViews(
                                                0,
                                                0,
                                                0,
                                                0
                                        );
                                    });

                        }
                )
                .addOnFailureListener(e -> {

                    firestore
                            .collection("attendance")
                            .document(uid)
                            .collection("records")
                            .whereGreaterThanOrEqualTo(
                                    "date",
                                    startDate
                            )
                            .whereLessThanOrEqualTo(
                                    "date",
                                    endDate
                            )
                            .get()
                            .addOnSuccessListener(
                                    attendanceSnapshot -> {

                                        calculateAttendanceSummary(
                                                attendanceSnapshot,
                                                calculationStart,
                                                calculationEnd,
                                                holidayDates,
                                                new HashSet<>()
                                        );

                                    }
                            )
                            .addOnFailureListener(error -> {

                                updateThisMonthViews(
                                        0,
                                        0,
                                        0,
                                        0
                                );
                            });
                });
    }


    // ============================================================
    // CALCULATE ATTENDANCE SUMMARY
    // ============================================================

    private void calculateAttendanceSummary(
            com.google.firebase.firestore.QuerySnapshot attendanceSnapshot,
            Calendar calculationStart,
            Calendar calculationEnd,
            Set<String> holidayDates,
            Set<String> approvedLeaveDates
    ) {

        Set<String> presentDates =
                new HashSet<>();


        for (DocumentSnapshot document :
                attendanceSnapshot.getDocuments()) {

            String date =
                    document.getString("date");


            if (date == null) {
                continue;
            }


            if (holidayDates.contains(date)) {
                continue;
            }


            if (approvedLeaveDates.contains(date)) {
                continue;
            }


            String status =
                    document.getString("status");


            if (status == null ||
                    status.trim().isEmpty() ||
                    status.equalsIgnoreCase("Present")) {

                presentDates.add(date);
            }
        }


        int workingDays = 0;


        Calendar current =
                (Calendar)
                        calculationStart.clone();


        while (!current.after(
                calculationEnd
        )) {

            int day =
                    current.get(
                            Calendar.DAY_OF_WEEK
                    );


            boolean isWeekend =
                    day == Calendar.SUNDAY;


            String currentDate =
                    formatDate(
                            current.getTime()
                    );


            boolean isHoliday =
                    holidayDates.contains(
                            currentDate
                    );


            boolean isApprovedLeave =
                    approvedLeaveDates.contains(
                            currentDate
                    );


            if (!isWeekend &&
                    !isHoliday &&
                    !isApprovedLeave) {

                workingDays++;
            }


            current.add(
                    Calendar.DAY_OF_MONTH,
                    1
            );
        }


        int presentDays =
                presentDates.size();


        int absentDays =
                Math.max(
                        0,
                        workingDays - presentDays
                );


        double percentage = 0;


        if (workingDays > 0) {

            percentage =
                    presentDays * 100.0
                            /
                            workingDays;
        }


        updateThisMonthViews(
                workingDays,
                presentDays,
                absentDays,
                percentage
        );
    }


    // ============================================================
    // ADD LEAVE DATES
    // ============================================================

    private void addLeaveDates(
            DocumentSnapshot document,
            Set<String> approvedLeaveDates,
            Calendar calculationStart,
            Calendar calculationEnd
    ) {

        String fromDate =
                document.getString("fromDate");


        String toDate =
                document.getString("toDate");


        if (fromDate == null) {
            return;
        }


        if (toDate == null ||
                toDate.trim().isEmpty()) {

            toDate = fromDate;
        }


        Date from =
                parseDate(fromDate);


        Date to =
                parseDate(toDate);


        if (from == null ||
                to == null) {

            return;
        }


        Calendar leaveStart =
                Calendar.getInstance();

        leaveStart.setTime(from);

        setStartOfDay(leaveStart);


        Calendar leaveEnd =
                Calendar.getInstance();

        leaveEnd.setTime(to);

        setStartOfDay(leaveEnd);


        if (leaveStart.before(
                calculationStart
        )) {

            leaveStart =
                    (Calendar)
                            calculationStart.clone();
        }


        if (leaveEnd.after(
                calculationEnd
        )) {

            leaveEnd =
                    (Calendar)
                            calculationEnd.clone();
        }


        Calendar current =
                (Calendar)
                        leaveStart.clone();


        while (!current.after(
                leaveEnd
        )) {

            int day =
                    current.get(
                            Calendar.DAY_OF_WEEK
                    );


            boolean isWeekend =
                    day == Calendar.SUNDAY;


            if (!isWeekend) {

                approvedLeaveDates.add(
                        formatDate(
                                current.getTime()
                        )
                );
            }


            current.add(
                    Calendar.DAY_OF_MONTH,
                    1
            );
        }
    }


    // ============================================================
    // UPDATE MONTHLY VIEWS
    // ============================================================

    private void updateThisMonthViews(
            int workingDays,
            int presentDays,
            int absentDays,
            double percentage
    ) {

        runOnUiThread(() -> {

            if (tvWorkingDays != null) {

                tvWorkingDays.setText(
                        String.valueOf(
                                workingDays
                        )
                );
            }


            if (tvPresentDays != null) {

                tvPresentDays.setText(
                        String.valueOf(
                                presentDays
                        )
                );
            }


            if (tvAbsentDays != null) {

                tvAbsentDays.setText(
                        String.valueOf(
                                absentDays
                        )
                );
            }


            if (tvAttendancePercentage != null) {

                tvAttendancePercentage.setText(
                        String.format(
                                Locale.getDefault(),
                                "%.0f%%",
                                percentage
                        )
                );
            }
        });
    }


    // ============================================================
    // PARSE DATE
    // ============================================================

    private Date parseDate(
            String dateString
    ) {

        if (dateString == null ||
                dateString.trim().isEmpty()) {

            return null;
        }


        String[] formats = {
                "yyyy-MM-dd",
                "dd-MM-yyyy",
                "dd/MM/yyyy"
        };


        for (String format : formats) {

            try {

                SimpleDateFormat sdf =
                        new SimpleDateFormat(
                                format,
                                Locale.getDefault()
                        );


                sdf.setLenient(false);


                return sdf.parse(
                        dateString.trim()
                );

            } catch (ParseException ignored) {
            }
        }


        return null;
    }


    // ============================================================
    // FORMAT DATE
    // ============================================================

    private String formatDate(
            Date date
    ) {

        return new SimpleDateFormat(
                "yyyy-MM-dd",
                Locale.getDefault()
        ).format(date);
    }


    // ============================================================
    // START OF DAY
    // ============================================================

    private void setStartOfDay(
            Calendar calendar
    ) {

        calendar.set(
                Calendar.HOUR_OF_DAY,
                0
        );

        calendar.set(
                Calendar.MINUTE,
                0
        );

        calendar.set(
                Calendar.SECOND,
                0
        );

        calendar.set(
                Calendar.MILLISECOND,
                0
        );
    }


    // ============================================================
    // FORMAT TIME
    // ============================================================

    private String formatTime(
            Timestamp timestamp
    ) {

        if (timestamp == null) {
            return "--";
        }


        return new SimpleDateFormat(
                "hh:mm a",
                Locale.getDefault()
        ).format(
                timestamp.toDate()
        );
    }


    // ============================================================
    // CALCULATE WORKING DURATION
    // ============================================================

    private String calculateWorkingDuration(
            Timestamp checkIn,
            Timestamp checkOut
    ) {

        if (checkIn == null ||
                checkOut == null) {

            return "--";
        }


        long difference =
                checkOut.toDate().getTime()
                        -
                        checkIn.toDate().getTime();


        if (difference < 0) {
            return "--";
        }


        long totalMinutes =
                difference /
                        (1000 * 60);


        long hours =
                totalMinutes / 60;


        long minutes =
                totalMinutes % 60;


        return String.format(
                Locale.getDefault(),
                "%02d hrs %02d mins",
                hours,
                minutes
        );
    }


    // ============================================================
    // PERMISSION RESULT
    // ============================================================

    @Override
    public void onRequestPermissionsResult(
            int requestCode,
            @NonNull String[] permissions,
            @NonNull int[] grantResults
    ) {

        super.onRequestPermissionsResult(
                requestCode,
                permissions,
                grantResults
        );


        // ========================================================
        // CAMERA
        // ========================================================

        if (requestCode ==
                CAMERA_PERMISSION_REQUEST_CODE) {

            boolean cameraGranted =
                    ActivityCompat.checkSelfPermission(
                            this,
                            Manifest.permission.CAMERA
                    ) == PackageManager.PERMISSION_GRANTED;


            if (cameraGranted) {

                openCameraForCheckIn();

            } else {

                Toast.makeText(
                        this,
                        "Camera permission is required for WFO check-in.",
                        Toast.LENGTH_LONG
                ).show();
            }


            return;
        }


        // ========================================================
        // LOCATION
        // ========================================================

        if (requestCode ==
                LOCATION_PERMISSION_REQUEST_CODE) {

            boolean fineGranted =
                    ActivityCompat.checkSelfPermission(
                            this,
                            Manifest.permission.ACCESS_FINE_LOCATION
                    ) == PackageManager.PERMISSION_GRANTED;


            boolean coarseGranted =
                    ActivityCompat.checkSelfPermission(
                            this,
                            Manifest.permission.ACCESS_COARSE_LOCATION
                    ) == PackageManager.PERMISSION_GRANTED;


            if (fineGranted || coarseGranted) {

                checkLocationAndCheckIn();

            } else {

                Toast.makeText(
                        this,
                        "Location permission is required for WFO check-in.",
                        Toast.LENGTH_LONG
                ).show();
            }
        }
    }


    // ============================================================
    // RESUME
    // ============================================================


    @Override
    protected void onResume() {

        super.onResume();

        if (firstResume) {
            firstResume = false;
            return;
        }

        loadTodayAttendance();
        loadThisMonthSummary();
        loadOfficeTimings();
    }



    // ============================================================
    // DESTROY
    // ============================================================

    @Override
    protected void onDestroy() {

        super.onDestroy();


        if (clockHandler != null &&
                clockRunnable != null) {

            clockHandler.removeCallbacks(
                    clockRunnable
            );
        }


        deleteTemporaryPhoto();
    }
}
