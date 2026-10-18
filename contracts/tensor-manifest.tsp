// Independently authored TypeSpec peer; generator drift parity is NOT yet verified.
import "@typespec/json-schema";
using TypeSpec.JsonSchema;

@minValue(0)
scalar NonnegativeExtent extends int32;

enum NumericDType {
  f32,
  f64,
}

@jsonSchema
model TensorManifest {
  schemaVersion: "oreslang.tensor-manifest/v1";
  dtype: NumericDType;
  device: "cpu";
  layout: "contiguous";
  shape: NonnegativeExtent[];
  storageLength: NonnegativeExtent;
}
