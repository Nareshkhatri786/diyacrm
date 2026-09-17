/** @odoo-module **/
import { Component, useState, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class AttendanceSelfieDialog extends Component {
    static template = "diyacrm.AttendanceSelfieDialog";
    static props = {
        close: Function,
        onSuccess: Function,
    };

    setup() {
        this.notification = useService("notification");
        this.videoRef = useRef("videoRef");
        this.mediaStream = null;

        this.state = useState({
            employeeName: "",
            isCheckedIn: false,
            workLat: 0.0,
            workLng: 0.0,
            allowedRadius: 150.0,
            requireSelfie: true,
            requireGeofence: true,

            cameraLoading: true,
            cameraError: false,
            cameraErrorMsg: "",
            capturedPhoto: null,

            currentLat: null,
            currentLng: null,
            distance: null,
            isWithinGeofence: false,
            geoError: false,
            geoTitle: "Fetching GPS location...",
            geoDescription: "Please wait while we verify your coordinates.",
            geoStatusColor: "#f8fafc",
            geoIcon: "fa-circle-o-notch fa-spin text-primary",

            canSubmit: false,
            submitting: false,
        });

        onMounted(async () => {
            await this.loadConfig();
            await this.startCamera();
            this.fetchLocation();
        });

        onWillUnmount(() => {
            this.stopCamera();
        });
    }

    async loadConfig() {
        try {
            const res = await rpc("/diyacrm/attendance/get_config");
            if (res.status === "success") {
                const c = res.config;
                this.state.employeeName = c.employee_name;
                this.state.isCheckedIn = (c.attendance_state === "checked_in");
                this.state.workLat = c.work_latitude;
                this.state.workLng = c.work_longitude;
                this.state.allowedRadius = c.geofence_radius || 150.0;
                this.state.requireSelfie = c.require_selfie;
                this.state.requireGeofence = c.require_geofence;
            }
        } catch (e) {
            console.error("Config fetch error:", e);
        }
    }

    async startCamera() {
        this.state.cameraLoading = true;
        this.state.cameraError = false;
        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error("Camera API not supported in this browser. Please use Chrome, Safari or Edge.");
            }
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: "user",
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                },
                audio: false
            });
            if (this.videoRef.el) {
                this.videoRef.el.srcObject = this.mediaStream;
            }
            this.state.cameraLoading = false;
        } catch (err) {
            this.state.cameraLoading = false;
            this.state.cameraError = true;
            if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
                this.state.cameraErrorMsg = "Camera access denied! Please click the lock/camera icon in your address bar and allow Camera.";
            } else {
                this.state.cameraErrorMsg = err.message || "Could not start camera.";
            }
        }
        this.updateSubmitState();
    }

    stopCamera() {
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
    }

    capturePhoto() {
        const video = this.videoRef.el;
        if (!video) return;

        try {
            const canvas = document.createElement("canvas");
            const w = video.videoWidth || 640;
            const h = video.videoHeight || 480;
            canvas.width = w;
            canvas.height = h;
            const ctx = canvas.getContext("2d");

            // 1. Draw Live Front Camera (Mirror)
            ctx.translate(w, 0);
            ctx.scale(-1, 1);
            ctx.drawImage(video, 0, 0, w, h);
            ctx.setTransform(1, 0, 0, 1, 0, 0);

            // 2. Anti-Spoof Security Watermark Banner
            ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
            ctx.fillRect(0, h - 55, w, 55);

            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 13px sans-serif";
            const now = new Date();
            const timeStr = now.toLocaleDateString("en-IN", {day: "2-digit", month: "short", year: "numeric"}) + " " + now.toLocaleTimeString("en-IN", {hour: "2-digit", minute: "2-digit", second: "2-digit"});
            const empName = this.state.employeeName || "Staff";
            const actionName = this.state.isCheckedIn ? "CLOCK OUT" : "CLOCK IN";
            ctx.fillText(`${actionName} | ${empName} | ${timeStr}`, 12, h - 32);

            ctx.fillStyle = "#4ade80";
            ctx.font = "11px sans-serif";
            const gpsInfo = this.state.currentLat ? `📍 GPS: ${this.state.currentLat.toFixed(5)}, ${this.state.currentLng.toFixed(5)} (${this.state.distance || 0}m)` : "📍 GPS Verified";
            ctx.fillText(`🛡️ LIVE VERIFIED CAPTURE | ${gpsInfo}`, 12, h - 14);

            this.state.capturedPhoto = canvas.toDataURL("image/jpeg", 0.85);
            this.stopCamera();
        } catch (e) {
            console.error("Capture photo error:", e);
        }
        this.updateSubmitState();
    }

    async retakePhoto() {
        this.state.capturedPhoto = null;
        await this.startCamera();
        this.updateSubmitState();
    }

    fetchLocation() {
        this.state.geoTitle = "Fetching GPS location...";
        this.state.geoDescription = "Getting high-accuracy satellite coordinates...";
        this.state.geoStatusColor = "#f8fafc";
        this.state.geoIcon = "fa-circle-o-notch fa-spin text-primary";
        this.state.geoError = false;

        if (!navigator.geolocation) {
            this.state.geoError = true;
            this.state.geoTitle = "GPS Not Supported";
            this.state.geoDescription = "Your browser does not support geolocation.";
            this.state.geoStatusColor = "#fef2f2";
            this.state.geoIcon = "fa-exclamation-triangle text-danger";
            this.updateSubmitState();
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = pos.coords.latitude;
                const lng = pos.coords.longitude;
                this.state.currentLat = lat;
                this.state.currentLng = lng;

                if (this.state.workLat && this.state.workLng) {
                    const dist = this.calculateDistance(lat, lng, this.state.workLat, this.state.workLng);
                    this.state.distance = Math.round(dist);
                    if (dist <= this.state.allowedRadius) {
                        this.state.isWithinGeofence = true;
                        this.state.geoTitle = "Location Verified (Inside Site)";
                        this.state.geoDescription = `You are ${Math.round(dist)}m from assigned site. Check-in/out allowed!`;
                        this.state.geoStatusColor = "#f0fdf4";
                        this.state.geoIcon = "fa-check-circle text-success";
                    } else {
                        this.state.isWithinGeofence = false;
                        this.state.geoTitle = "Outside Work Location";
                        this.state.geoDescription = `You are ${Math.round(dist)}m away. Allowed radius is ${this.state.allowedRadius}m.`;
                        this.state.geoStatusColor = "#fef2f2";
                        this.state.geoIcon = "fa-times-circle text-danger";
                    }
                } else {
                    this.state.isWithinGeofence = true;
                    this.state.geoTitle = "GPS Coordinates Captured";
                    this.state.geoDescription = `Lat: ${lat.toFixed(5)}, Lng: ${lng.toFixed(5)}`;
                    this.state.geoStatusColor = "#f0fdf4";
                    this.state.geoIcon = "fa-map-marker text-success";
                }
                this.updateSubmitState();
            },
            (err) => {
                this.state.geoError = true;
                this.state.isWithinGeofence = false;
                this.state.geoStatusColor = "#fef2f2";
                this.state.geoIcon = "fa-exclamation-circle text-danger";
                if (err.code === 1) {
                    this.state.geoTitle = "Location Permission Denied";
                    this.state.geoDescription = "Please enable GPS & allow location access in your browser settings.";
                } else {
                    this.state.geoTitle = "Location Timeout / Error";
                    this.state.geoDescription = "Could not fetch GPS signal. Please move to open area and retry.";
                }
                this.updateSubmitState();
            },
            { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
        );
    }

    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371000;
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    updateSubmitState() {
        const hasLiveVideo = !this.state.cameraError && !this.state.cameraLoading;
        const validSelfie = !this.state.requireSelfie || !!this.state.capturedPhoto || hasLiveVideo;
        const validLocation = !this.state.requireGeofence || this.state.isWithinGeofence;
        this.state.canSubmit = validSelfie && validLocation;
    }

    async submitAttendance() {
        if (this.state.submitting) return;

        if (!this.state.capturedPhoto && this.videoRef.el && !this.state.cameraError) {
            this.capturePhoto();
        }

        if (this.state.requireSelfie && !this.state.capturedPhoto) {
            this.notification.add("Live camera selfie is required to record attendance.", {
                title: "Live Camera Required",
                type: "danger"
            });
            return;
        }

        if (this.state.requireGeofence && !this.state.isWithinGeofence) {
            this.notification.add(this.state.geoDescription, {
                title: this.state.geoTitle,
                type: "danger"
            });
            return;
        }

        this.state.submitting = true;
        try {
            const res = await rpc("/diyacrm/attendance/check_in_out", {
                photo: this.state.capturedPhoto,
                latitude: this.state.currentLat,
                longitude: this.state.currentLng,
            });

            this.notification.add(res.message || "Attendance recorded!", {
                title: "Attendance Successful",
                type: "success",
                sticky: false,
            });

            if (this.props.onSuccess) {
                await this.props.onSuccess();
            }
            this.props.close();
        } catch (error) {
            console.error("Attendance submission error:", error);
            this.notification.add(error.data ? error.data.message : error.message, {
                title: "Attendance Blocked",
                type: "danger",
                sticky: true,
            });
        } finally {
            this.state.submitting = false;
        }
    }

    closeModal() {
        this.stopCamera();
        this.props.close();
    }
}
