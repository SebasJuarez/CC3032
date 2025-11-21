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

print("[SETUP] Inicializando arreglo people de tamaño 3");

let p0: Person = new Person("Ana");
print("[NEW] Creado objeto Person p0 con nombre Ana");
p0.init("Ana");
print("[INIT] p0.init completado");
people[0] = p0;
print("[ARRAY] people[0] asignado a Ana");

let p1: Student = new Student("Ben", 90);
print("[NEW] Creado objeto Student p1 con nombre Ben y grade 90");
p1.init("Ben", 90);
print("[INIT] p1.init completado");
people[1] = p1;
print("[ARRAY] people[1] asignado a Ben");

let p2: Student = new Student("Cami", 95);
print("[NEW] Creado objeto Student p2 con nombre Cami y grade 95");
p2.init("Cami", 95);
print("[INIT] p2.init completado");
people[2] = p2;
print("[ARRAY] people[2] asignado a Cami");

print("[INFO] Comenzando recorrido del arreglo people (for i=0..n, incluye OOB para probar catch)");

try {
    for (let i: integer = 0; i <= n; i = i + 1) {
        people[i].greet();
    }
} catch (IndexOutOfBounds) { 
    print("INDEX_OOB"); 
}

print("[TEST] Intentando división por cero para activar catch correspondiente");

try {
    let x: integer = 10 / 0;
    print(x);
} catch (DivisionByZero) { 
    print("DIV_ZERO"); 
}

print("[FINAL] PRUEBAS DE ARRAYS CHECK");
print("[DONE] Fin del script OK-3");