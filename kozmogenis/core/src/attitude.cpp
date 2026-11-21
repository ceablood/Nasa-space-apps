#include "kozmo/attitude.hpp"

#include <algorithm>
#include <cmath>

namespace kozmo::attitude {

namespace {
constexpr double kG0 = 9.80665;
double clampd(double v, double a) { return std::clamp(v, -a, a); }
}  // namespace

double V3::norm() const { return std::sqrt(x * x + y * y + z * z); }

Quat Quat::operator*(const Quat& o) const {
    return {w * o.w - x * o.x - y * o.y - z * o.z, w * o.x + x * o.w + y * o.z - z * o.y, w * o.y - x * o.z + y * o.w + z * o.x,
            w * o.z + x * o.y - y * o.x + z * o.w};
}

Quat Quat::normalized() const {
    const double n = std::sqrt(w * w + x * x + y * y + z * z);
    return n > 0 ? Quat{w / n, x / n, y / n, z / n} : Quat{};
}

V3 Quat::rotate(const V3& v) const {
    const Quat p{0, v.x, v.y, v.z};
    const Quat r = (*this) * p * conj();
    return {r.x, r.y, r.z};
}

Quat Quat::from_axis_angle(V3 a, double rad) {
    const double n = a.norm();
    if (n <= 0) return {};
    const double s = std::sin(rad / 2) / n;
    return {std::cos(rad / 2), a.x * s, a.y * s, a.z * s};
}

double Quat::angle_to(const Quat& o) const {
    const double d = std::fabs(w * o.w + x * o.x + y * o.y + z * o.z);
    return 2.0 * std::acos(std::clamp(d, -1.0, 1.0));
}

const char* to_string(Sas s) {
    switch (s) {
        case Sas::Off: return "SAS kapalı";
        case Sas::KillRotation: return "Dönüşü durdur";
        case Sas::Hold: return "Yönelimi tut";
        case Sas::Target: return "Hedefe yönel";
    }
    return "?";
}

Body::Body(Config c) : c_(c) {}

void Body::set_sas(Sas m) {
    sas_ = m;
    hold_ = q_;
}

V3 Body::control_torque(double dt) {
    (void)dt;
    const V3 I = c_.inertia;
    V3 want_acc;                                  // istenen açısal ivme (rad/s^2)
    const bool stick = input_.norm() > 1e-6;
    if (sas_ == Sas::Off || stick) {
        // doğrudan kontrol kolu: RCS torku oransal
        return {input_.x * c_.rcs_torque, input_.y * c_.rcs_torque, input_.z * c_.rcs_torque};
    }
    auto pd = [&](const Quat& goal) {
        // hata kuaterniyonu q_e = q^-1 * goal (gövde çerçevesinde); kısa yol için w>=0
        Quat e = q_.conj() * goal;
        if (e.w < 0) e = {-e.w, -e.x, -e.y, -e.z};
        const V3 err{2 * e.x, 2 * e.y, 2 * e.z};
        return err * c_.kp - w_ * c_.kd;
    };
    switch (sas_) {
        case Sas::KillRotation: want_acc = w_ * (-c_.kd); break;
        case Sas::Hold: want_acc = pd(hold_); break;
        case Sas::Target: want_acc = pd(target_); break;
        case Sas::Off: break;
    }
    // rasyonel kazanç: atalete göre tork, ardından sınırlama
    return {want_acc.x * I.x * 0.02, want_acc.y * I.y * 0.02, want_acc.z * I.z * 0.02};
}

void Body::step(double dt) {
    if (dt <= 0) return;
    V3 tau = control_torque(dt);
    // tekerlekler önce (yakıtsız); sınırını aşan kısım ya da doyma -> RCS
    V3 wheel{clampd(tau.x, c_.wheel_torque), clampd(tau.y, c_.wheel_torque), clampd(tau.z, c_.wheel_torque)};
    V3 hn = h_ - wheel * dt;   // tekerlek, gövdeye uyguladığı torkun tersini momentum olarak depolar
    auto sat = [&](double& hv, double& wv) {
        if (std::fabs(hv) > c_.wheel_capacity) {
            wv = 0;   // doymuş eksende tekerlek tork veremez
            hv = std::copysign(c_.wheel_capacity, hv);
        }
    };
    sat(hn.x, wheel.x);
    sat(hn.y, wheel.y);
    sat(hn.z, wheel.z);
    h_ = hn;
    V3 rcs = tau - wheel;
    rcs = {clampd(rcs.x, c_.rcs_torque), clampd(rcs.y, c_.rcs_torque), clampd(rcs.z, c_.rcs_torque)};
    // RCS yakıtı: her eksende tork / moment kolu kadar itki, iki itici (çift) ateşlenir
    const double arm = c_.rcs_torque / c_.rcs_thrust;
    const double thrust = (std::fabs(rcs.x) + std::fabs(rcs.y) + std::fabs(rcs.z)) / arm;
    prop_kg_ += thrust * dt / (c_.rcs_isp * kG0);
    const V3 total = wheel + rcs + dist_;
    // Euler: w' = I^-1 (tau - w x I w); açısal hız RK4, kuaterniyon her alt adımda üstel güncelleme
    const V3 I = c_.inertia;
    auto f = [&](const V3& w) {
        const V3 Iw{I.x * w.x, I.y * w.y, I.z * w.z};
        const V3 g = w.cross(Iw);
        return V3{(total.x - g.x) / I.x, (total.y - g.y) / I.y, (total.z - g.z) / I.z};
    };
    const V3 k1 = f(w_), k2 = f(w_ + k1 * (dt / 2)), k3 = f(w_ + k2 * (dt / 2)), k4 = f(w_ + k3 * dt);
    const V3 wn = w_ + (k1 + k2 * 2 + k3 * 2 + k4) * (dt / 6);
    const V3 wm = (w_ + wn) * 0.5;
    const double ang = wm.norm() * dt;
    if (ang > 1e-12) q_ = (q_ * Quat::from_axis_angle(wm, ang)).normalized();   // tam dönüş (kesin, kuaterniyon üstel)
    w_ = wn;
}

double Body::rotational_energy() const {
    const V3 I = c_.inertia;
    return 0.5 * (I.x * w_.x * w_.x + I.y * w_.y * w_.y + I.z * w_.z * w_.z);
}

V3 Body::angular_momentum_world() const {
    const V3 I = c_.inertia;
    const V3 Lb{I.x * w_.x + h_.x, I.y * w_.y + h_.y, I.z * w_.z + h_.z};   // gövde + tekerlek
    return q_.rotate(Lb);
}

}  // namespace kozmo::attitude
