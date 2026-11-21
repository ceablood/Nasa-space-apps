// KozmoCore — uzay aracı tutum dinamiği ve kontrolü (V30 §14.2, V41 §1.3 kontrol kolu, §2.5 dönüş).
//
// Fizik (gerçek): katı cisim Euler denklemleri I w' + w x (I w) = tau; tutum kuaterniyonu q' = 1/2 q (x) [0, w];
// RCS tork = itki x moment kolu; reaksiyon tekerleği momentumu sınırlı (doyunca RCS ile boşaltılır).
// Kontrol: SAS (kararlılık destek) modları — dönüşü durdur, yönelimi tut, hedef yönelime dön (PD kontrol,
// kuaterniyon hata vektörü). Kazançlar ve atalet değerleri mühendislik yaklaşımıdır (ör. Dragon ~10 t, RCS
// Draco 400 N; ISS CMG'leri ~4760 N m s — tekerlek doyma örneği).
#pragma once

#include <string>

#include "kozmo/core.hpp"

namespace kozmo::attitude {

struct V3 {
    double x = 0, y = 0, z = 0;
    V3 operator+(const V3& o) const { return {x + o.x, y + o.y, z + o.z}; }
    V3 operator-(const V3& o) const { return {x - o.x, y - o.y, z - o.z}; }
    V3 operator*(double k) const { return {x * k, y * k, z * k}; }
    double dot(const V3& o) const { return x * o.x + y * o.y + z * o.z; }
    V3 cross(const V3& o) const { return {y * o.z - z * o.y, z * o.x - x * o.z, x * o.y - y * o.x}; }
    double norm() const;
};

struct Quat {
    double w = 1, x = 0, y = 0, z = 0;
    Quat operator*(const Quat& o) const;
    Quat conj() const { return {w, -x, -y, -z}; }
    Quat normalized() const;
    V3 rotate(const V3& v) const;                    // gövde -> dünya
    static Quat from_axis_angle(V3 axis, double rad);
    double angle_to(const Quat& o) const;            // iki yönelim arası açı (rad)
};

enum class Sas { Off, KillRotation, Hold, Target };
const char* to_string(Sas s);

struct Config {
    V3 inertia{8000, 8000, 5000};    // kg m^2 (köşegen)
    double rcs_torque = 400.0 * 2.0; // N m (400 N x 2 m kol)
    double rcs_isp = 300.0;
    double rcs_thrust = 400.0;       // N (tork başına yanma)
    double wheel_torque = 0.3;       // N m
    double wheel_capacity = 50.0;    // N m s (doyma)
    double kp = 0.6, kd = 2.5;       // PD kazançları (açısal ivme birimi)
};

class Body {
public:
    explicit Body(Config c = {});
    const Quat& q() const { return q_; }
    const V3& omega() const { return w_; }           // gövde ekseninde rad/s
    const V3& wheel_momentum() const { return h_; }
    double rcs_propellant_used() const { return prop_kg_; }
    void set_omega(V3 w) { w_ = w; }
    void set_attitude(Quat q) { q_ = q.normalized(); }

    // pilot girişi (-1..1 her eksen): kontrol kolu; SAS kapalıysa doğrudan tork
    void set_input(V3 stick) { input_ = stick; }
    void set_sas(Sas m);
    Sas sas() const { return sas_; }
    void set_target(Quat t) { target_ = t.normalized(); }
    // dış bozucu tork (ör. yerçekimi gradyanı, asimetrik itki), N m
    void set_disturbance(V3 t) { dist_ = t; }

    void step(double dt);
    double rotational_energy() const;                // 1/2 w . I w
    V3 angular_momentum_world() const;               // gövde + tekerlek, dünya çerçevesi

private:
    V3 control_torque(double dt);
    Config c_;
    Quat q_, target_, hold_;
    V3 w_, h_, input_, dist_;
    Sas sas_ = Sas::Off;
    double prop_kg_ = 0;
};

}  // namespace kozmo::attitude
