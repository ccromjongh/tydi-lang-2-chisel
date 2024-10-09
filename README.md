# Tydi-lang-2-Chisel

Tydi-lang-2-Chisel is a transpiler that takes [tydi-lang-2](https://github.com/twoentartian/tydi-lang-2)'s `json` output of a Tydi-lang description and converts it to Chisel code that uses [Tydi-Chisel](https://github.com/abs-tudelft/Tydi-Chisel). See the Tydi-Chisel repo for more details.

## How to use
In total, the process looks as follows:
1. Create a Tydi-lang system description (`td` file) of the data-types, streams, interfaces (`streamlets`), and components (`impl`ementations).
2. Compile the `td` file with `tydi-lang-complier -c .\tydi_project.toml` with configuration file specifying the `td` sources and top level implementation.
    1. Acquire the executable by cloning and compiling the project (e.g. `cargo build`).
3. Generate Chisel code with e.g.
    ```shell
    python3 -m tl2chisel ./output ./td-json-output/json_IR.json
    ```
   - You can opt to install the module with `pip3 install -e .`.
4. Use the resulting Chisel code in your project.

Check `python3 -m tl2chisel -h` to see options. Multiple input files can be specified. These are all processed individually. If no input file is specified, an `stdin` input is expected.

## Simple demo

To see what the program in action without acquiring your own TydiLang code, simply run
```shell
python3 -m tl2chisel ./output json_output.json 
```
This will transpile the output of the following TydiLang code.

```C
package pack0;

bit_4 = Bit(4);
bit_8 = Bit(8);
bit_16 = Bit(16);

#this is an union size#
Union size {
   small : bit_4;
   mid : bit_8;
   large : bit_16;
}

stream_size = Stream(size);
```
```C
package pack1;
use pack0;

#this is a streamlet#
streamlet bypass_s {
   # this is port_in #
   port_in: pack0.stream_size in;
   
   # this is port_out #
   port_out: pack0.stream_size out;
}

#this is an implementation#
impl bypass_i_inner of bypass_s {
   self.port_in => self.port_out;
}

impl bypass_i of bypass_s {
   # this instance is used to test using an implementation without template expansion #
   instance test_inst(bypass_i_inner);

   # ports on self have "opposite" direction #
   self.port_in => test_inst.port_in;
   test_inst.port_out => self.port_out;
}
```

This will result in the following output.

```scala
package pack1

import nl.tudelft.tydi_chisel._
import chisel3._
import chisel3.experimental.ExtModule

object MyTypes {
    /** Bit(8) type, defined in package [[pack0]] */
    def bit_8: UInt = UInt(8.W)
    assert(this.bit_8.getWidth == 8)

    /** Bit(4) type, defined in package [[pack0]] */
    def bit_4: UInt = UInt(4.W)
    assert(this.bit_4.getWidth == 4)

    /** Bit(16) type, defined in package [[pack0]] */
    def bit_16: UInt = UInt(16.W)
    assert(this.bit_16.getWidth == 16)
}


/** Stream, defined in package [[pack0]]. */
class Stream_size extends PhysicalStreamDetailed(e=new Size, n=1, d=1, c=1, r=false, u=Null())

object Stream_size {
    def apply(): Stream_size = Wire(new Stream_size())
}

/** Bit(8), defined in package [[pack0]]. */
class Bit_8 extends BitsEl(8.W)

/** Bit(4), defined in package [[pack0]]. */
class Bit_4 extends BitsEl(4.W)

/** Bit(16), defined in package [[pack0]]. */
class Bit_16 extends BitsEl(16.W)

/** Union element, defined in package [[pack0]].
 * This is an union size. */
class Size extends Union(3) {
    val large = MyTypes.bit_16
    val mid = MyTypes.bit_8
    val small = MyTypes.bit_4
}

/**
 * Streamlet, defined in package [[pack1]].
 * This is a streamlet.
 */
class Bypass_s extends TydiModule {
    /** Stream of [[port_in]] with input direction. This is port_in. */
    protected val port_inStream: PhysicalStreamDetailed[Size, Null] = Stream_size().flip
    /** IO of [[port_inStream]] with input direction. */
    val port_in: PhysicalStream = port_inStream.toPhysical

    /** Stream of [[port_out]] with output direction. This is port_out. */
    protected val port_outStream: PhysicalStreamDetailed[Size, Null] = Stream_size()
    /** IO of [[port_outStream]] with output direction. */
    val port_out: PhysicalStream = port_outStream.toPhysical
}

/**
 * Implementation, defined in package [[pack1]].
 */
class Bypass_i extends Bypass_s {
    // Fixme: Remove the following line if this impl. contains logic. If it just interconnects, remove this comment.
    port_inStream := DontCare
    // Fixme: Remove the following line if this impl. contains logic. If it just interconnects, remove this comment.
    port_outStream := DontCare

    // Modules
    /** This instance is used to test using an implementation without template expansion. */
    private val test_inst = Module(new Bypass_i_inner)

    // Connections
    /* Ports on self have "opposite" direction. */
    test_inst.port_in := port_in
    port_out := test_inst.port_out
}

/**
 * Implementation, defined in package [[pack1]].
 * This is an implementation.
 */
class Bypass_i_inner extends Bypass_s {
    // Fixme: Remove the following line if this impl. contains logic. If it just interconnects, remove this comment.
    port_inStream := DontCare
    // Fixme: Remove the following line if this impl. contains logic. If it just interconnects, remove this comment.
    port_outStream := DontCare

    // Connections
    port_out := port_in
}
```
