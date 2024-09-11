// scala-cli directives, ignore if using in sbt project
//> using scala "2.13.12"
//> using dep "org.chipsalliance::chisel:6.5.0"
//> using plugin "org.chipsalliance:::chisel-plugin:6.5.0"
//> using options "-unchecked", "-deprecation", "-language:reflectiveCalls", "-feature", "-Xcheckinit", "-Xfatal-warnings",
//> using dep "nl.tudelft::tydi-chisel::0.1.0"

package {{ compile_options.package_of_top_level_implementation }}

import {{ compile_options.package_of_top_level_implementation }}.{{ compile_options.top_level_implementation | capitalize }}

import chisel3._
// _root_ disambiguates from package chisel3.util.circt if user imports chisel3.util._
import _root_.circt.stage.ChiselStage
import nl.tudelft.tydi_chisel._

import java.io.{File, FileWriter}

object {{ compile_options.package_of_top_level_implementation | snake2pascal }} extends App {
  // Print stream compatibility issues as warnings. Can be removed once the system is fine-tuned.
  nl.tudelft.tydi_chisel.setCompatCheckResult(CompatCheckResult.Warning)

  // Generate the Verilog output
  private val {{ compile_options.top_level_implementation | snake2camel }}Verilog: String = ChiselStage.emitSystemVerilog(new {{ compile_options.top_level_implementation | capitalize }})

  println({{ compile_options.top_level_implementation | snake2camel }}Verilog)
  private val writer = new FileWriter(new File("{{ output_dir }}/{{ compile_options.package_of_top_level_implementation }}.v"))
  writer.write({{ compile_options.top_level_implementation | snake2camel }}Verilog)
  writer.close()
}
