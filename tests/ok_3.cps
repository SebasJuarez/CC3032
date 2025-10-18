// OK-3: Clases/objetos, herencia, arreglos, control de flujo y try/catch
class Person {
    var name: string;
    function init(n: string): void { this.name = n; }
    function greet(): void { print(this.name); }
}

class Student : Person {
    var grade: integer;
    function init(n: string, g: integer): void { this.name = n; this.grade = g; }
    function greet(): void { print(this.name); print(this.grade); }
}

let n: integer = 3;
let people: person[] = new person[3];

let p0: Person = new Person("Ana");
p0.init("Ana");
people[0] = p0;

let p1: Student = new Student("Ben", 90);
p1.init("Ben", 90);
people[1] = p1;

let p2: Student = new Student("Cami", 95);
p2.init("Cami", 95);
people[2] = p2;

try {
    for (let i: integer = 0; i <= n; i = i + 1) {
        people[i].greet();
    }
} catch (IndexOutOfBounds) { print("INDEX_OOB"); }

try {
    let x: integer = 10 / 0;
    print(x);
} catch (DivisionByZero) { print("DIV_ZERO"); }
