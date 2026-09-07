import { z } from "zod";

export const W63AuthorityEnvelope = z.object({
  logicalId: z.string().min(1),
  authorityPath: z.string().min(1),
  manifestSource: z.literal("ssot/manifest.yaml"),
  payloadSha256: z.string().regex(/^[a-f0-9]{64}$/),
  returnedPayloadSha256: z.string().regex(/^[a-f0-9]{64}$/),
  authority: z.literal("AUTHORITATIVE_REFERENCE_ONLY"),
}).superRefine((value, ctx) => {
  if (value.payloadSha256 !== value.returnedPayloadSha256) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "federation zero-delta SHA256 mismatch",
    });
  }
});

export type W63AuthorityEnvelope = z.infer<typeof W63AuthorityEnvelope>;
