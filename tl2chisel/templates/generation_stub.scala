// scala-cli directives, ignore if using in sbt project
//> using scala "2.13.12"
//> using dep "org.chipsalliance::chisel::5.1.0"
//> using dep "nl.tudelft::tydi-chisel::0.1.0"
//> using plugin "org.chipsalliance:::chisel-plugin::5.1.0"
//> using options "-unchecked", "-deprecation", "-language:reflectiveCalls", "-feature", "-Xcheckinit", "-Xfatal-warnings", "-Ywarn-dead-code", "-Ywarn-unused", "-Ymacro-annotations"

package {{ compile_options.package_of_top_level_implementation }}

import {{ compile_options.package_of_top_level_implementation }}.{{ compile_options.top_level_implementation | capitalize }}

import chisel3._
import circt.stage.ChiselStage

import java.io.{File, FileWriter}

object {{ compile_options.package_of_top_level_implementation | snake2pascal }} extends App {
  // Generate the Verilog output
  private val {{ compile_options.top_level_implementation | snake2camel }}Verilog: String = ChiselStage.emitSystemVerilog(new {{ compile_options.top_level_implementation | capitalize }})

  println({{ compile_options.top_level_implementation | snake2camel }}Verilog)
  private val writer = new FileWriter(new File("{{ output_dir }}/{{ compile_options.package_of_top_level_implementation }}.v"))
  writer.write({{ compile_options.top_level_implementation | snake2camel }}Verilog)
  writer.close()
}
