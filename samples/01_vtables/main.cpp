// Sample 01: virtual functions, vtables and RTTI.
//
// What to look for in a disassembler:
//  * each class with virtual functions gets a vtable (an array of function
//    pointers) and the object's first 8 bytes point at it;
//  * a call through Shape* loads that pointer and calls an entry at a fixed
//    offset. GCC puts the two destructors in slots 0 and 1, so area() is
//    slot 2 (`call [rax+0x10]`) and name() is slot 3 (`call [rax+0x18]`);
//  * typeid/dynamic_cast use the RTTI records that sit next to the vtable.
#include <cstdio>
#include <memory>
#include <typeinfo>
#include <vector>

struct Shape {
    virtual ~Shape() = default;
    virtual double area() const = 0;
    virtual const char* name() const { return "shape"; }
};

struct Circle final : Shape {
    explicit Circle(double r) : radius(r) {}
    double area() const override { return 3.0 * radius * radius; }
    const char* name() const override { return "circle"; }
    double radius;
};

struct Square final : Shape {
    explicit Square(double s) : side(s) {}
    double area() const override { return side * side; }
    const char* name() const override { return "square"; }
    double side;
};

int main() {
    std::vector<std::unique_ptr<Shape>> shapes;
    shapes.push_back(std::make_unique<Circle>(2.0));
    shapes.push_back(std::make_unique<Square>(3.0));

    double total = 0;
    for (const auto& s : shapes) {
        std::printf("%s %.1f\n", s->name(), s->area());
        total += s->area();
    }
    int squares = 0;
    for (const auto& s : shapes) {
        if (dynamic_cast<const Square*>(s.get()) != nullptr) ++squares;
    }
    std::printf("total %.1f squares %d\n", total, squares);
    return 0;
}
