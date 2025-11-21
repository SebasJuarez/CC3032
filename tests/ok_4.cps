// OK-4: Sentencias de control (if, else-if, else, while, do-while, for, foreach, break, continue, switch)

// if / else-if / else
let x: integer = 5;
if (x < 0) {
    print("neg");
} else if (x == 0) {
    print("zero");
} else {
    print("pos");
}

// while
let i: integer = 0;
while (i < 3) {
    print(i);
    i = i + 1;
}

// do-while
let j: integer = 0;
do {
    print(j);
    j = j + 1;
} while (j < 2);

// for (init; cond; step)
for (let k: integer = 0; k < 2; k = k + 1) {
    print(k);
}

// foreach sobre arreglo
let arr: integer[] = new integer[3];
arr[0] = 10;
arr[1] = 20;
arr[2] = 30;
foreach (v in arr) {
    print(v);
}

// break y continue
let t: integer = 0;
while (t < 5) {
    t = t + 1;
    if (t == 2) { continue; }
    if (t == 4) { break; }
    print(t);
}

// switch (si tu gramática lo soporta)
let jum: integer = 1;
switch (jum) {
    case 0: print("cero");
    case 1: print("uno");
    default: print("otro");
}
